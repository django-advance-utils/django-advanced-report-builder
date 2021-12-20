import base64
import copy
import json

from ajax_helpers.mixins import AjaxHelpers
from crispy_forms.bootstrap import StrictButton
from crispy_forms.layout import Div
from django.apps import apps
from django.db.models import Count, Sum
from django.db.models.functions import Coalesce
from django.forms import CharField, ChoiceField, BooleanField
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView
from django_datatables.datatables import HorizontalTable
from django_menus.menu import MenuMixin, MenuItem
from django_modals.fields import FieldEx
from django_modals.forms import CrispyForm
from django_modals.modals import FormModal
from django_modals.processes import PROCESS_EDIT_DELETE, PERMISSION_OFF
from django_modals.widgets.colour_picker import ColourPickerWidget
from django_modals.widgets.select2 import Select2

from advanced_report_builder.columns import ReportBuilderNumberColumn, ReportBuilderDateColumn
from advanced_report_builder.filter_query import FilterQueryMixin
from advanced_report_builder.globals import NUMBER_FIELDS, ANNOTATION_FUNCTIONS, BOOLEAN_FIELD, DATE_FIELDS, \
    ANNOTATION_VALUE_FUNCTIONS, DATE_FORMAT_TYPES_DJANGO_FORMAT, DATE_FORMAT_TYPE_DD_MM_YY_SLASH
from advanced_report_builder.models import SingleValueReport, BarChartReport, ReportType
from advanced_report_builder.toggle import RBToggle
from advanced_report_builder.utils import split_slug, get_django_field, split_attr
from advanced_report_builder.views.modals_base import QueryBuilderModalBase, QueryBuilderModalBaseMixin


class BarChartView(AjaxHelpers, FilterQueryMixin, MenuMixin, TemplateView):
    number_field = ReportBuilderNumberColumn
    date_field = ReportBuilderDateColumn
    template_name = 'advanced_report_builder/bar_charts/report.html'

    def __init__(self, *args, **kwargs):
        self.bar_chart_report = None
        self.show_toolbar = False
        super().__init__(*args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        self.slug = split_slug(kwargs.get('slug'))
        self.report = kwargs.get('report')
        self.bar_chart_report = self.report.barchartreport
        self.enable_edit = kwargs.get('enable_edit')
        self.dashboard_report = kwargs.get('dashboard_report')
        if self.enable_edit or (self.dashboard_report and not self.dashboard_report.top) or not self.dashboard_report:
            self.show_toolbar = True
        return super().dispatch(request, *args, **kwargs)

    def extra_filters(self, query):
        report_query = self.get_report_query(report=self.bar_chart_report)
        if not report_query:
            return query

        return self.process_query_filters(query=query,
                                          search_filter_data=report_query.query)

    def get_aggregation_field(self, fields, field_name, col_type_override, aggregations_type, decimal_places=0):

        if col_type_override:
            field = copy.deepcopy(col_type_override)
            if aggregations_type == 'count':
                new_field_name = f'{aggregations_type}_{field_name}'
                number_function_kwargs = {}
                function = ANNOTATION_FUNCTIONS[aggregations_type]
                number_function_kwargs['annotations'] = {new_field_name: function(field.field)}

                number_function_kwargs.update({'field': new_field_name,
                                               'column_name': field_name})
                field = self.number_field(**number_function_kwargs)
            else:
                if aggregations_type:
                    new_field_name = f'{aggregations_type}_{field_name}'

                    function = ANNOTATION_FUNCTIONS[aggregations_type]
                    field.aggregations = {new_field_name: function(field.field)}
                    field.field = new_field_name
                    field.options['calculated'] = True

            fields.append(field)
        else:
            number_function_kwargs = {}
            if decimal_places:
                number_function_kwargs = {'decimal_places': int(decimal_places)}

            if aggregations_type:
                new_field_name = f'{aggregations_type}_{field_name}'
                function = ANNOTATION_FUNCTIONS[aggregations_type]
                number_function_kwargs['aggregations'] = {new_field_name: function(field_name)}
                field_name = new_field_name

            number_function_kwargs.update({'field': field_name,
                                           'column_name': field_name,
                                           'options': {'calculated': True},
                                           'model_path': ''})

            field = self.number_field(**number_function_kwargs)
            fields.append(field)

        return field_name

    def _process_aggregations(self, fields, aggregations_type='sum'):
        field = self.bar_chart_report.field
        base_modal = self.bar_chart_report.get_base_modal()

        django_field, col_type_override, _ = get_django_field(base_modal=base_modal, field=field)

        if isinstance(django_field, NUMBER_FIELDS) or isinstance(django_field, BOOLEAN_FIELD):
            self.get_aggregation_field(fields=fields,
                                       field_name=field,
                                       col_type_override=col_type_override,
                                       aggregations_type=aggregations_type,
                                       decimal_places=self.bar_chart_report.decimal_places)
        else:
            assert False, 'not a number field'

    def _get_count(self, fields):

        number_function_kwargs = {'aggregations': {'count': Count(1)},
                                  'field': 'count',
                                  'column_name': 'count',
                                  'options': {'calculated': True},
                                  'model_path': ''}

        field = self.number_field(**number_function_kwargs)
        fields.append(field)

    def get_percentage_field(self, fields,
                             numerator_field_name, numerator_col_type_override,
                             denominator_field_name, denominator_col_type_override,
                             numerator_filter, decimal_places=0):
        if numerator_col_type_override:
            actual_numerator_field_name = numerator_col_type_override.field
        else:
            actual_numerator_field_name = numerator_field_name

        if denominator_col_type_override:
            actual_denominator_field_name = denominator_col_type_override.field
        else:
            actual_denominator_field_name = denominator_field_name

        number_function_kwargs = {}
        if decimal_places:
            number_function_kwargs = {'decimal_places': int(decimal_places)}

        new_field_name = f'{actual_numerator_field_name}_{actual_denominator_field_name}'

        if numerator_filter:
            numerator = Coalesce((Sum(actual_numerator_field_name, filter=numerator_filter)+0.0), 0.0)
        else:
            numerator = Coalesce((Sum(actual_numerator_field_name) + 0.0), 0.0)
        denominator = Coalesce(Sum(actual_denominator_field_name) + 0.0, 0.0)

        number_function_kwargs['aggregations'] = {new_field_name: (numerator / denominator) * 100.0}
        field_name = new_field_name

        number_function_kwargs.update({'field': field_name,
                                       'column_name': field_name,
                                       'options': {'calculated': True},
                                       'model_path': ''})

        field = self.number_field(**number_function_kwargs)

        fields.append(field)

        return field_name

    def _process_percentage(self, fields):
        denominator_field = self.bar_chart_report.field
        numerator_field = self.bar_chart_report.numerator
        base_modal = self.bar_chart_report.get_base_modal()

        deno_django_field, denominator_col_type_override, _ = get_django_field(base_modal=base_modal,
                                                                               field=denominator_field)

        num_django_field, numerator_col_type_override, _ = get_django_field(base_modal=base_modal,
                                                                            field=denominator_field)

        if ((isinstance(deno_django_field, NUMBER_FIELDS) or isinstance(deno_django_field, BOOLEAN_FIELD)) and
                (isinstance(num_django_field, NUMBER_FIELDS) or isinstance(num_django_field, BOOLEAN_FIELD))):
            numerator_filter = None
            report_query = self.get_report_query(report=self.bar_chart_report)
            if report_query:
                numerator_filter = self.process_filters(search_filter_data=report_query.extra_query)

            self.get_percentage_field(fields=fields,
                                      numerator_field_name=numerator_field,
                                      numerator_col_type_override=numerator_col_type_override,
                                      denominator_field_name=denominator_field,
                                      denominator_col_type_override=denominator_col_type_override,
                                      numerator_filter=numerator_filter,
                                      decimal_places=2,
                                      )
        else:
            assert False, 'not a number field'

    def _process_percentage_from_count(self, fields):
        report_query = self.get_report_query(report=self.bar_chart_report)

        numerator_filter = None
        if report_query:
            numerator_filter = self.process_filters(search_filter_data=report_query.extra_query)

        if numerator_filter:
            numerator = Coalesce(Count(1, filter=numerator_filter) + 0.0, 0.0)
        else:
            numerator = Coalesce(Count(1) + 0.0, 0.0)
        denominator = Coalesce(Count(1) + 0.0, 0.0)
        a = (numerator / denominator) * 100.0

        number_function_kwargs = {'aggregations': {'count': a},
                                  'field': 'count',
                                  'column_name': 'count',
                                  'options': {'calculated': True},
                                  'model_path': ''}
        decimal_places = self.bar_chart_report.decimal_places
        if decimal_places:
            number_function_kwargs['decimal_places'] = int(decimal_places)

        field = self.number_field(**number_function_kwargs)
        fields.append(field)


    def get_date_field(self, index, fields):
        date_format = DATE_FORMAT_TYPES_DJANGO_FORMAT[DATE_FORMAT_TYPE_DD_MM_YY_SLASH]
        field_name = self.bar_chart_report.date_field
        date_function_kwargs = {'title': field_name,
                                'date_format': date_format}

        annotations_value = self.bar_chart_report.axis_scale

        new_field_name = f'{annotations_value}_{field_name}_{index}'
        function = ANNOTATION_VALUE_FUNCTIONS[annotations_value]
        date_function_kwargs['annotations_value'] = {new_field_name: function(field_name)}
        field_name = new_field_name

        date_function_kwargs.update({'field': field_name,
                                     'column_name': field_name,
                                     'options': {'calculated': True},
                                     'model_path': ''})

        field = self.date_field(**date_function_kwargs)
        fields.append(field)
        return field_name


    def process_query_results(self):
        axis_value_type = self.bar_chart_report.axis_value_type
        fields = []

        self.get_date_field(1, fields)

        if axis_value_type == SingleValueReport.SINGLE_VALUE_TYPE_COUNT:
            self._get_count(fields=fields)
        elif axis_value_type == SingleValueReport.SINGLE_VALUE_TYPE_SUM:
            self._process_aggregations(fields=fields, aggregations_type='sum')
        elif axis_value_type == SingleValueReport.SINGLE_VALUE_TYPE_COUNT_AND_SUM:
            self._get_count(fields=fields)
            self._process_aggregations(fields=fields, aggregations_type='sum')
        elif axis_value_type == SingleValueReport.SINGLE_VALUE_TYPE_AVERAGE:
            self._process_aggregations(fields=fields, aggregations_type='avg')
        elif axis_value_type == SingleValueReport.SINGLE_VALUE_TYPE_PERCENT:
            self._process_percentage(fields=fields)
        elif axis_value_type == SingleValueReport.SINGLE_VALUE_TYPE_PERCENT_FROM_COUNT:
            self._process_percentage_from_count(fields=fields)
        return fields

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_modal = self.bar_chart_report.get_base_modal()

        table = HorizontalTable(model=base_modal)
        table.datatable_template = 'advanced_report_builder/bar_charts/middle.html'
        table.extra_filters = self.extra_filters

        fields = self.process_query_results()
        table.add_columns(
            *fields
        )
        context['datatable'] = table
        context['bar_chart_report'] = self.bar_chart_report
        context['title'] = self.get_title()
        return context

    def setup_menu(self):
        super().setup_menu()
        if not self.show_toolbar:
            return

        if self.dashboard_report and self.enable_edit:
            report_menu = self.pod_dashboard_edit_menu()
        elif self.dashboard_report and not self.enable_edit:
            report_menu = self.pod_dashboard_view_menu()
        else:
            report_menu = self.pod_report_menu()

        self.add_menu('button_menu', 'button_group').add_items(
            *report_menu,
            *self.queries_menu(),
        )

    def pod_dashboard_edit_menu(self):
        return [MenuItem(f'advanced_report_builder:dashboard_report_modal,pk-{self.dashboard_report.id}',
                         menu_display='Edit',
                         font_awesome='fas fa-pencil-alt', css_classes=['btn-primary'])]

    def pod_dashboard_view_menu(self):
        return []

    def pod_report_menu(self):

        query_id = self.slug.get(f'query{self.bar_chart_report.id}')
        slug_str = ''
        if query_id:
            slug_str = f'-query_id-{query_id}'

        return [MenuItem(f'advanced_report_builder:bar_chart_modal,pk-{self.bar_chart_report.id}{slug_str}',
                         menu_display='Edit',
                         font_awesome='fas fa-pencil-alt', css_classes=['btn-primary'])]

    def queries_menu(self):
        return []


class BarChartModal(QueryBuilderModalBase):
    template_name = 'advanced_report_builder/bar_charts/modal.html'
    process = PROCESS_EDIT_DELETE
    permission_delete = PERMISSION_OFF
    model = BarChartReport
    widgets = {'positive_bar_colour': ColourPickerWidget,
               'negative_bar_colour': ColourPickerWidget,
               'show_totals': RBToggle}

    form_fields = ['name',
                   'report_type',
                   ('bar_chart_orientation', {'label': 'Orientation'}),
                   'axis_value_type',
                   'axis_scale',
                   'date_field',
                   'fields',
                   'x_label',
                   'y_label',
                   'show_totals',
                   ]

    def form_setup(self, form, *_args, **_kwargs):
        #     form.add_trigger('single_value_type', 'onchange', [
        #         {'selector': '#div_id_field',
        #          'values': {SingleValueReport.SINGLE_VALUE_TYPE_COUNT: 'hide',
        #                     SingleValueReport.SINGLE_VALUE_TYPE_PERCENT_FROM_COUNT: 'hide'},
        #          'default': 'show'},
        #         {'selector': '#div_id_numerator',
        #          'values': {SingleValueReport.SINGLE_VALUE_TYPE_PERCENT: 'show'},
        #          'default': 'hide'},
        #         {'selector': '#div_id_extra_query_data',
        #          'values': {SingleValueReport.SINGLE_VALUE_TYPE_PERCENT: 'show',
        #                     SingleValueReport.SINGLE_VALUE_TYPE_PERCENT_FROM_COUNT: 'show'},
        #          'default': 'hide'},
        #         {'selector': 'label[for=id_field]',
        #          'values': {SingleValueReport.SINGLE_VALUE_TYPE_PERCENT: ('html', 'Denominator field')},
        #          'default': ('html', 'Field')},
        #     ])
        #
        #     fields = []
        #     if form.instance.field:
        #
        #         form.fields['field'].initial = form.instance.field
        #
        #         base_model = form.instance.report_type.content_type.model_class()
        #         report_builder_fields = getattr(base_model, form.instance.report_type.report_builder_class_name, None)
        #
        #         self._get_fields(base_model=base_model,
        #                          fields=fields,
        #                          report_builder_fields=report_builder_fields,
        #                          selected_field_id=form.instance.field)
        #
        #     form.fields['field'].widget = Select2(attrs={'ajax': True})
        #     form.fields['field'].widget.select_data = fields
        #
        #     form.fields['numerator'].widget = Select2(attrs={'ajax': True})
        #     form.fields['numerator'].widget.select_data = fields
        #

        date_fields = []
        if form.instance.date_field:

            form.fields['fields'].initial = form.instance.fields

            base_model = form.instance.report_type.content_type.model_class()
            report_builder_fields = getattr(base_model, form.instance.report_type.report_builder_class_name, None)

            self._get_date_fields(base_model=base_model,
                                  fields=date_fields,
                                  report_builder_fields=report_builder_fields,
                                  selected_field_id=form.instance.fields)

        form.fields['date_field'].widget = Select2(attrs={'ajax': True})
        form.fields['date_field'].widget.select_data = date_fields

        self.add_query_data(form, include_extra_query=True)
        return ('name',
                'report_type',
                'bar_chart_orientation',
                'axis_scale',
                'axis_value_type',
                'date_field',
                FieldEx('fields', template='advanced_report_builder/bar_charts/fields/select_column.html'),
                'x_label',
                'y_label',
                'show_totals',
                FieldEx('query_data',
                        template='advanced_report_builder/query_builder.html'),
                )
    #
    # def form_valid(self, form):
    #     single_value_report = form.save()
    #
    #     if not self.report_query and (form.cleaned_data['query_data'] or form.cleaned_data['extra_query_data']):
    #         ReportQuery(query=form.cleaned_data['query_data'],
    #                     extra_query=form.cleaned_data['extra_query_data'],
    #                     report=single_value_report).save()
    #     elif form.cleaned_data['query_data'] or form.cleaned_data['extra_query_data']:
    #         self.report_query.extra_query = form.cleaned_data['extra_query_data']
    #         self.report_query.query = form.cleaned_data['query_data']
    #         if self.show_query_name:
    #             self.report_query.name = form.cleaned_data['query_name']
    #         self.report_query.save()
    #     elif self.report_query:
    #         self.report_query.delete()
    #
    #     return self.command_response('reload')
    #
    # def clean(self, form, cleaned_data):
    #     if (cleaned_data['single_value_type'] not in [SingleValueReport.SINGLE_VALUE_TYPE_COUNT,
    #                                                   SingleValueReport.SINGLE_VALUE_TYPE_PERCENT_FROM_COUNT] and
    #             not cleaned_data['field']):
    #         raise ValidationError("Please select a field")

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
            django_field, _, columns = get_django_field(base_modal=base_model, field=report_builder_field)
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

    def _get_fields(self, base_model, fields, tables, report_builder_fields,
                    prefix='', title_prefix='', title=None, colour=None):
        if title is None:
            title = report_builder_fields.title
        if colour is None:
            colour = report_builder_fields.colour

        tables.append({'name': title,
                       'colour': colour})

        for report_builder_field in report_builder_fields.fields:
            django_field, _, columns = get_django_field(base_modal=base_model, field=report_builder_field)
            for column in columns:
                if isinstance(django_field, NUMBER_FIELDS):
                    fields.append({'field': prefix + column.column_name,
                                   'label': title_prefix + column.title,
                                   'colour': report_builder_fields.colour})

        for include in report_builder_fields.includes:
            app_label, model, report_builder_fields_str = include['model'].split('.')
            new_model = apps.get_model(app_label, model)
            new_report_builder_fields = getattr(new_model, report_builder_fields_str, None)
            self._get_fields(base_model=new_model,
                             fields=fields,
                             tables=tables,
                             report_builder_fields=new_report_builder_fields,
                             prefix=f"{include['field']}__",
                             title_prefix=include['title'] + ' -> ',
                             title=include.get('title'),
                             colour=include.get('colour'))

    def ajax_get_fields(self, **kwargs):
        report_type_id = kwargs['report_type'][0]
        report_builder_fields, base_model = self.get_report_builder_fields(report_type_id=report_type_id)

        fields = []
        tables = []
        self._get_fields(base_model=base_model,
                         fields=fields,
                         tables=tables,
                         report_builder_fields=report_builder_fields)
        return self.command_response('report_fields', data=json.dumps({'fields': fields, 'tables': tables}))


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
        self.django_field, _, _ = get_django_field(base_modal=base_model, field=data['field'])

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
    template_name = 'advanced_report_builder/bar_charts/fields/modal.html'

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
