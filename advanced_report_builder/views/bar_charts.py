import base64
import json

from crispy_forms.bootstrap import StrictButton
from crispy_forms.layout import Div
from django.apps import apps
from django.forms import CharField, ChoiceField, BooleanField
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django_menus.menu import MenuItem
from django_modals.fields import FieldEx
from django_modals.forms import CrispyForm
from django_modals.modals import FormModal
from django_modals.processes import PROCESS_EDIT_DELETE, PERMISSION_OFF
from django_modals.widgets.colour_picker import ColourPickerWidget
from django_modals.widgets.select2 import Select2, Select2Multiple

from advanced_report_builder.globals import NUMBER_FIELDS, DATE_FIELDS, DEFAULT_DATE_FORMAT, \
    DATE_FORMAT_TYPES_DJANGO_FORMAT
from advanced_report_builder.models import BarChartReport, ReportType, ReportQuery
from advanced_report_builder.toggle import RBToggle
from advanced_report_builder.utils import get_django_field, split_attr
from advanced_report_builder.views.charts_base import ChartBaseView, ChartBaseModal
from advanced_report_builder.views.modals_base import QueryBuilderModalBaseMixin


class BarChartView(ChartBaseView):

    def dispatch(self, request, *args, **kwargs):
        self.report = kwargs.get('report')
        self.chart_report = self.report.barchartreport
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.table.bar_chart_report = self.chart_report
        self.table.datatable_template = 'advanced_report_builder/charts/bar/middle.html'
        context['bar_chart_report'] = self.chart_report
        return context

    def get_date_format(self):
        if self.chart_report.show_blank_dates:
            date_format = '%Y-%m-%d'
        else:
            default_format_type = DEFAULT_DATE_FORMAT[self.chart_report.axis_scale]
            date_format = DATE_FORMAT_TYPES_DJANGO_FORMAT[default_format_type]
        return date_format

    def set_extra_number_field_kwargs(self, data_attr, options, multiple_index):
        negative_bar_colour = data_attr.get('negative_bar_colour') or '801C70'
        positive_bar_colour = data_attr.get('positive_bar_colour') or '801C70'
        negative_bar_colour = self.add_colour_offset(negative_bar_colour, multiple_index=multiple_index)
        positive_bar_colour = self.add_colour_offset(positive_bar_colour, multiple_index=multiple_index)

        options.update({'colours': {'negative': negative_bar_colour,
                                    'positive': positive_bar_colour}})

    def pod_report_menu(self):
        query_id = self.slug.get(f'query{self.chart_report.id}')
        slug_str = ''
        if query_id:
            slug_str = f'-query_id-{query_id}'

        return [MenuItem(f'advanced_report_builder:bar_chart_modal,pk-{self.chart_report.id}{slug_str}',
                         menu_display='Edit',
                         font_awesome='fas fa-pencil-alt', css_classes=['btn-primary'])]


class BarChartModal(ChartBaseModal):
    template_name = 'advanced_report_builder/charts/modal.html'
    process = PROCESS_EDIT_DELETE
    permission_delete = PERMISSION_OFF
    model = BarChartReport
    widgets = {'positive_bar_colour': ColourPickerWidget,
               'negative_bar_colour': ColourPickerWidget,
               'stacked': RBToggle,
               'show_totals': RBToggle,
               'show_blank_dates': RBToggle,
               'report_tags': Select2Multiple}

    form_fields = ['name',
                   'report_type',
                   'report_tags',
                   ('bar_chart_orientation', {'label': 'Orientation'}),
                   'axis_value_type',
                   'axis_scale',
                   'date_field',
                   'fields',
                   'x_label',
                   'y_label',
                   'stacked',
                   'show_totals',
                   'show_blank_dates',
                   ]

    def form_setup(self, form, *_args, **_kwargs):

        date_fields = []
        if form.instance.date_field:

            form.fields['fields'].initial = form.instance.fields

            base_model = form.instance.report_type.content_type.model_class()
            report_builder_fields = getattr(base_model, form.instance.report_type.report_builder_class_name, None)

            self._get_date_fields(base_model=base_model,
                                  fields=date_fields,
                                  report_builder_fields=report_builder_fields,
                                  selected_field_id=form.instance.date_field)

        form.fields['date_field'].widget = Select2(attrs={'ajax': True})
        form.fields['date_field'].widget.select_data = date_fields

        self.add_query_data(form, include_extra_query=True)
        url = reverse('advanced_report_builder:bar_chart_field_modal',
                      kwargs={'slug': 'selector-99999-data-FIELD_INFO-report_type_id-REPORT_TYPE_ID'})

        return ('name',
                'report_type',
                'report_tags',
                'bar_chart_orientation',
                'axis_scale',
                'axis_value_type',
                'date_field',
                FieldEx('fields',
                        template='advanced_report_builder/select_column.html',
                        extra_context={'select_column_url': url}),
                'x_label',
                'y_label',
                'stacked',
                'show_totals',
                'show_blank_dates',
                FieldEx('query_data',
                        template='advanced_report_builder/query_builder.html'),
                )

    def form_valid(self, form):
        bar_chart_report = form.save()

        if not self.report_query and (form.cleaned_data['query_data'] or form.cleaned_data['extra_query_data']):
            ReportQuery(query=form.cleaned_data['query_data'],
                        extra_query=form.cleaned_data['extra_query_data'],
                        report=bar_chart_report).save()
        elif form.cleaned_data['query_data'] or form.cleaned_data['extra_query_data']:
            self.report_query.extra_query = form.cleaned_data['extra_query_data']
            self.report_query.query = form.cleaned_data['query_data']
            if self.show_query_name:
                self.report_query.name = form.cleaned_data['query_name']
            self.report_query.save()
        elif self.report_query:
            self.report_query.delete()

        return self.command_response('reload')

    def select2_date_field(self, **kwargs):
        fields = []
        if kwargs['report_type'] != '':
            report_builder_fields, base_model = self.get_report_builder_fields(report_type_id=kwargs['report_type'])
            fields = []
            self._get_date_fields(base_model=base_model,
                                  fields=fields,
                                  report_builder_fields=report_builder_fields)

        return JsonResponse({'results': fields})

    def _get_date_fields(self, base_model, fields, report_builder_fields,
                         prefix='', title_prefix='', selected_field_id=None):

        for report_builder_field in report_builder_fields.fields:
            django_field, _, columns = get_django_field(base_model=base_model, field=report_builder_field)
            for column in columns:
                if isinstance(django_field, DATE_FIELDS):
                    full_id = prefix + column.column_name
                    if selected_field_id is None or selected_field_id == full_id:
                        fields.append({'id': full_id,
                                       'text': title_prefix + column.title})

        for include in report_builder_fields.includes:
            app_label, model, report_builder_fields_str = include['model'].split('.')
            new_model = apps.get_model(app_label, model)
            new_report_builder_fields = getattr(new_model, report_builder_fields_str, None)
            self._get_date_fields(base_model=new_model,
                                  fields=fields,
                                  report_builder_fields=new_report_builder_fields,
                                  prefix=f"{include['field']}__",
                                  title_prefix=include['title'] + ' -> ')


class BarChartFieldForm(CrispyForm):

    def __init__(self, *args, **kwargs):
        self.django_field = None
        super().__init__(*args, **kwargs)

    def submit_button(self, css_class='btn-success modal-submit', button_text='Submit', **kwargs):
        if isinstance(self.django_field, NUMBER_FIELDS):
            return StrictButton(button_text, onclick=f'save_modal_{self.form_id}()', css_class=css_class, **kwargs)
        else:
            return super().submit_button(css_class, button_text, **kwargs)

    def get_report_type_details(self):
        data = json.loads(base64.b64decode(self.slug['data']))

        report_type = get_object_or_404(ReportType, pk=self.slug['report_type_id'])
        base_model = report_type.content_type.model_class()
        self.django_field, _, _ = get_django_field(base_model=base_model, field=data['field'])

        return report_type, base_model

    def setup_modal(self, *args, **kwargs):
        data = json.loads(base64.b64decode(self.slug['data']))
        report_type, base_model = self.get_report_type_details()

        data_attr = split_attr(data)

        self.fields['title'] = CharField(initial=data['title'])

        self.fields['positive_bar_colour'] = CharField(required=False, widget=ColourPickerWidget)
        self.fields['negative_bar_colour'] = CharField(required=False, widget=ColourPickerWidget)
        self.fields['positive_bar_colour'].initial = data_attr.get('positive_bar_colour')
        self.fields['negative_bar_colour'].initial = data_attr.get('negative_bar_colour')

        self.fields['has_filter'] = BooleanField(required=False, widget=RBToggle())
        self.fields['filter'] = CharField(required=False)

        if data_attr.get('has_filter') == '1':
            self.fields['has_filter'].initial = True
            if 'filter' in data_attr:
                _filter = base64.urlsafe_b64decode(data_attr['filter'])
                _filter = _filter.decode('utf-8', 'ignore')
                self.fields['filter'].initial = _filter

        self.fields['multiple_columns'] = BooleanField(required=False, widget=RBToggle())

        report_builder_fields = getattr(base_model, report_type.report_builder_class_name, None)
        fields = []
        self._get_query_builder_foreign_key_fields(report_builder_fields=report_builder_fields,
                                                   fields=fields)

        self.fields['multiple_column_field'] = ChoiceField(choices=fields, required=False)

        if data_attr.get('multiple_columns') == '1':
            self.fields['multiple_columns'].initial = True
            self.fields['multiple_column_field'].initial = data_attr.get('multiple_column_field')

        super().setup_modal(*args, **kwargs)

    def get_additional_attributes(self):
        attributes = []
        self.get_report_type_details()

        attributes.append(f'positive_bar_colour-{self.cleaned_data["positive_bar_colour"]}')
        attributes.append(f'negative_bar_colour-{self.cleaned_data["negative_bar_colour"]}')

        if self.cleaned_data['has_filter']:
            attributes.append('has_filter-1')

            if self.cleaned_data['filter']:
                _filter = self.cleaned_data['filter'].encode('utf-8', 'ignore')
                b64_filter = base64.urlsafe_b64encode(_filter).decode('utf-8', 'ignore')
                attributes.append(f'filter-{b64_filter}')

            if self.cleaned_data['multiple_columns']:
                attributes.append('multiple_columns-1')
                attributes.append(f'multiple_column_field-{self.cleaned_data["multiple_column_field"]}')

        if attributes:
            return '-'.join(attributes)
        return None

    def _get_query_builder_foreign_key_fields(self, report_builder_fields, fields,
                                              prefix='', title_prefix=''):
        for include in report_builder_fields.includes:
            app_label, model, report_builder_fields_str = include['model'].split('.')
            new_model = apps.get_model(app_label, model)
            new_report_builder_fields = getattr(new_model, report_builder_fields_str, None)
            fields.append((prefix + include['field'], title_prefix + include['title']))

            self._get_query_builder_foreign_key_fields(report_builder_fields=new_report_builder_fields,
                                                       fields=fields,
                                                       prefix=f"{include['field']}__",
                                                       title_prefix=f"{include['title']} --> ")


class BarChartFieldModal(QueryBuilderModalBaseMixin, FormModal):
    form_class = BarChartFieldForm
    size = 'xl'
    template_name = 'advanced_report_builder/charts/modal.html'

    @property
    def modal_title(self):
        data = json.loads(base64.b64decode(self.slug['data']))
        return f'Edit {data["title"]}'

    def form_valid(self, form):
        selector = self.slug['selector']

        _attr = form.get_additional_attributes()
        self.add_command({'function': 'set_attr',
                          'selector': f'#{selector}',
                          'attr': 'data-attr',
                          'val': _attr})

        self.add_command({'function': 'html', 'selector': f'#{selector} span', 'html': form.cleaned_data['title']})
        self.add_command({'function': 'save_query_builder_id_query_data'})
        self.add_command({'function': 'update_selection'})
        return self.command_response('close')

    # noinspection PyMethodMayBeStatic
    def form_setup(self, form, *_args, **_kwargs):
        form.add_trigger('has_filter', 'onchange', [
            {'selector': '#filter_fields_div', 'values': {'checked': 'show'}, 'default': 'hide'}])

        form.add_trigger('multiple_columns', 'onchange', [
            {'selector': '#multiple_columns_fields_div', 'values': {'checked': 'show'}, 'default': 'hide'},
        ])

        return ['title',
                'positive_bar_colour',
                'negative_bar_colour',
                Div(FieldEx('has_filter',
                            template='django_modals/fields/label_checkbox.html',
                            field_class='col-6 input-group-sm'),
                    Div(
                        FieldEx('filter',
                                template='advanced_report_builder/datatables/fields/single_query_builder.html'),
                        FieldEx('multiple_columns',
                                template='django_modals/fields/label_checkbox.html',
                                field_class='col-6 input-group-sm'),
                        Div(
                            FieldEx('multiple_column_field'),
                            css_id='multiple_columns_fields_div'),
                        css_id='filter_fields_div'),
                    css_id='annotations_fields_div')
                ]

    def ajax_get_query_builder_fields(self, **kwargs):
        field_auto_id = kwargs['field_auto_id'][0]

        report_type_id = self.slug['report_type_id']
        query_builder_filters = self.get_query_builder_report_type_field(report_type_id=report_type_id)

        return self.command_response(f'query_builder_{field_auto_id}', data=json.dumps(query_builder_filters))
