import base64
import json

from crispy_forms.layout import Div
from django.core.exceptions import FieldDoesNotExist
from django.forms import CharField, ChoiceField, BooleanField
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django_datatables.datatables import DatatableTable
from django_menus.menu import MenuItem
from django_modals.fields import FieldEx
from django_modals.form_helpers import HorizontalNoEnterHelper
from django_modals.modals import FormModal, Modal
from django_modals.processes import PROCESS_EDIT_DELETE, PERMISSION_OFF
from django_modals.widgets.colour_picker import ColourPickerWidget
from django_modals.widgets.select2 import Select2Multiple
from django_modals.widgets.widgets import Toggle

from advanced_report_builder.exceptions import ReportError
from advanced_report_builder.globals import DEFAULT_DATE_FORMAT, \
    DATE_FORMAT_TYPES_DJANGO_FORMAT
from advanced_report_builder.models import BarChartReport, ReportType
from advanced_report_builder.toggle import RBToggle
from advanced_report_builder.utils import split_attr, encode_attribute, decode_attribute, get_field_details
from advanced_report_builder.views.charts_base import ChartBaseView, ChartBaseFieldForm
from advanced_report_builder.views.datatables.utils import TableUtilsMixin
from advanced_report_builder.views.modals_base import QueryBuilderModalBaseMixin, QueryBuilderModalBase


class BarChartView(ChartBaseView):

    def dispatch(self, request, *args, **kwargs):
        self.report = kwargs.get('report')
        self.chart_report = self.report.barchartreport
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        try:
            context = super().get_context_data(**kwargs)
        except FieldDoesNotExist as e:
            raise ReportError(e)
        self.table.bar_chart_report = self.chart_report
        self.table.datatable_template = 'advanced_report_builder/charts/bar/middle.html'
        self.table.breakdown_url = self.get_breakdown_url()

        context['bar_chart_report'] = self.chart_report
        return context

    def get_breakdown_url(self):
        if self.table.bar_chart_report.show_breakdown:
            enable_links = self.slug.get('enable_links') == 'True'
            slug = f'pk-{self.table.bar_chart_report.id}-data-99999-index-88888-enable_links-{enable_links}'
            return reverse('advanced_report_builder:bar_chart_show_breakdown_modal',
                           kwargs={'slug': slug})
        return None

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

    def edit_report_menu(self, request, chart_report_id, slug_str):
        return [MenuItem(f'advanced_report_builder:bar_chart_modal,pk-{chart_report_id}{slug_str}',
                         menu_display='Edit',
                         font_awesome='fas fa-pencil-alt', css_classes=['btn-primary']),
                *self.duplicate_menu(request=self.request, report_id=chart_report_id)
                ]


class BarChartModal(QueryBuilderModalBase):
    template_name = 'advanced_report_builder/charts/modal.html'
    process = PROCESS_EDIT_DELETE
    permission_delete = PERMISSION_OFF
    model = BarChartReport
    widgets = {'positive_bar_colour': ColourPickerWidget,
               'negative_bar_colour': ColourPickerWidget,
               'stacked': RBToggle,
               'show_totals': RBToggle,
               'show_blank_dates': RBToggle,
               'report_tags': Select2Multiple,
               'show_breakdown': Toggle(attrs={'data-onstyle': 'success', 'data-on': 'YES', 'data-off': 'NO'})}

    form_fields = ['name',
                   'notes',
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
                   'show_breakdown',
                   'breakdown_fields']

    def form_setup(self, form, *_args, **_kwargs):
        if 'data' in _kwargs:
            date_field = _kwargs['data'].get('date_field')
            report_type_id = _kwargs['data'].get('report_type')
            report_type = get_object_or_404(ReportType, id=report_type_id)
        else:
            date_field = form.instance.date_field
            report_type = form.instance.report_type

        self.setup_field(field_type='date',
                         form=form,
                         field_name='date_field',
                         selected_field_id=date_field,
                         report_type=report_type)

        form.fields['notes'].widget.attrs['rows'] = 3

        self.add_query_data(form)
        url = reverse('advanced_report_builder:bar_chart_field_modal',
                      kwargs={'slug': 'selector-99999-data-FIELD_INFO-report_type_id-REPORT_TYPE_ID'})

        url_breakdown = None

        form.add_trigger('show_breakdown', 'onchange', [
            {'selector': '#div_id_breakdown_fields', 'values': {'checked': 'show'}, 'default': 'hide'},
        ])

        return ('name',
                'notes',
                'report_type',
                'report_tags',
                'bar_chart_orientation',
                'axis_scale',
                'axis_value_type',
                'date_field',
                FieldEx('fields',
                        template='advanced_report_builder/select_column.html',
                        extra_context={'select_column_url': url,
                                       'command_prefix': ''}),
                'x_label',
                'y_label',
                'stacked',
                'show_totals',
                'show_blank_dates',
                'show_breakdown',
                FieldEx('breakdown_fields',
                        template='advanced_report_builder/select_column.html',
                        extra_context={'select_column_url': url_breakdown,
                                       'command_prefix': 'breakdown_'}),
                FieldEx('query_data',
                        template='advanced_report_builder/query_builder.html'),
                )

    def select2_date_field(self, **kwargs):
        return self.get_fields_for_select2(field_type='date',
                                           report_type=kwargs['report_type'],
                                           search_string=kwargs.get('search'))

    def _get_ajax_fields(self, report_type, prefix=''):
        report_type_id = report_type
        report_builder_fields, base_model = self.get_report_builder_class(report_type_id=report_type_id)
        fields = []
        tables = []
        self._get_fields(base_model=base_model,
                         fields=fields,
                         tables=tables,
                         report_builder_class=report_builder_fields)

        self.add_command(f'{prefix}report_fields', data=json.dumps({'fields': fields, 'tables': tables}))
        return self.command_response()

    def ajax_get_fields(self, **kwargs):
        return self._get_ajax_fields(report_type=kwargs['report_type'])

    def ajax_get_breakdown_fields(self, **kwargs):
        return self._get_ajax_fields(report_type=kwargs['report_type'],
                                     prefix='breakdown_')


class BarChartFieldForm(ChartBaseFieldForm):

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
                self.fields['filter'].initial = decode_attribute(data_attr['filter'])

        self.fields['multiple_columns'] = BooleanField(required=False, widget=RBToggle())

        report_builder_fields = getattr(base_model, report_type.report_builder_class_name, None)
        fields = []
        self._get_query_builder_foreign_key_fields(base_model=base_model,
                                                   report_builder_fields=report_builder_fields,
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
                b64_filter = encode_attribute(self.cleaned_data['filter'])
                attributes.append(f'filter-{b64_filter}')

            if self.cleaned_data['multiple_columns']:
                attributes.append('multiple_columns-1')
                attributes.append(f'multiple_column_field-{self.cleaned_data["multiple_column_field"]}')

        if attributes:
            return '-'.join(attributes)
        return None


class BarChartFieldModal(QueryBuilderModalBaseMixin, FormModal):
    form_class = BarChartFieldForm
    size = 'xl'
    template_name = 'advanced_report_builder/charts/modal_field.html'
    no_header_x = True
    helper_class = HorizontalNoEnterHelper

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
        self.add_command({'function': 'breakdown_update_selection'})
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
        field_auto_id = kwargs['field_auto_id']

        report_type_id = self.slug['report_type_id']
        query_builder_filters = self.get_query_builder_report_type_field(report_type_id=report_type_id)

        return self.command_response(f'query_builder_{field_auto_id}', data=json.dumps(query_builder_filters))


class BarChartShowBreakdownModal(TableUtilsMixin, Modal):
    button_container_class = 'text-center'
    size = 'xl'

    def modal_title(self):
        # return self.table_report.name
        return 'hello world'

    def add_table(self, base_model):
        return DatatableTable(view=self, model=base_model)

    def setup_table(self):
        bar_chart_report = get_object_or_404(BarChartReport, pk=self.slug['pk'])
        self.kwargs['enable_links'] = self.slug['enable_links'] == 'True'
        base_model = bar_chart_report.get_base_modal()
        chart_fields = bar_chart_report.fields
        report_builder_class = getattr(base_model,
                                       bar_chart_report.report_type.report_builder_class_name, None)
        table = self.add_table(base_model=base_model)
        # table.extra_filters = self.extra_filters
        table_fields = bar_chart_report.breakdown_fields
        fields_used = set()
        self.process_query_results(report_builder_class=report_builder_class,
                                   table=table,
                                   base_model=base_model,
                                   fields_used=fields_used,
                                   table_fields=table_fields)


        for index, table_field in enumerate(chart_fields, 1):
            field = table_field['field']

            django_field, col_type_override, _, _ = get_field_details(base_model=base_model,
                                                                      field=field,
                                                                      report_builder_class=report_builder_class,
                                                                      table=table)




        table.ajax_data = False
        table.table_options['pageLength'] = 25
        table.table_options['bStateSave'] = False
        return table

    def modal_content(self):
        table = self.setup_table()
        return table.render()
