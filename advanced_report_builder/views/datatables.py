import base64
import copy
import json

from ajax_helpers.mixins import AjaxHelpers
from django.apps import apps
from django.shortcuts import get_object_or_404
from django_datatables.datatables import DatatableView, ColumnInitialisor
from django_datatables.plugins.column_totals import ColumnTotals
from django_menus.menu import MenuMixin, MenuItem
from django_modals.fields import FieldEx
from django_modals.modals import FormModal
from django_modals.processes import PROCESS_EDIT_DELETE, PERMISSION_OFF
from django_modals.widgets.widgets import Toggle

from advanced_report_builder.columns import ReportBuilderDateColumn, ReportBuilderNumberColumn
from advanced_report_builder.filter_query import FilterQueryMixin
from advanced_report_builder.forms import FieldForm
from advanced_report_builder.globals import DATE_FORMAT_TYPES_DJANGO_FORMAT, ANNOTATION_VALUE_FUNCTIONS, DATE_FIELDS, \
    ANNOTATION_FUNCTIONS, NUMBER_FIELDS
from advanced_report_builder.models import TableReport, ReportType, ReportQuery
from advanced_report_builder.utils import split_attr, split_slug, get_django_field
from advanced_report_builder.views.modals_base import QueryBuilderModalBase


class TableView(AjaxHelpers, FilterQueryMixin, MenuMixin, DatatableView):
    template_name = 'advanced_report_builder/datatable.html'

    date_field = ReportBuilderDateColumn
    number_field = ReportBuilderNumberColumn

    def add_tables(self):
        return None

    def dispatch(self, request, *args, **kwargs):
        self.slug = split_slug(self.kwargs['slug'])
        self.report = kwargs.get('report')
        self.table_report = self.report.tablereport
        self.dashboard_report = kwargs.get('dashboard_report')
        self.enable_edit = kwargs.get('enable_edit')
        if self.dashboard_report:
            table_id = f'tabledashboard_{self.dashboard_report.id}'
        else:
            table_id = f'table_{self.table_report.id}'

        base_model = self.table_report.get_base_modal()
        self.add_table(table_id, model=base_model)
        return super().dispatch(request, *args, **kwargs)

    def get_date_field(self, table_field, fields):
        data_attr = split_attr(table_field)
        field_name = table_field['field']
        date_format = data_attr.get('date_format')
        if date_format:
            date_format = DATE_FORMAT_TYPES_DJANGO_FORMAT[int(date_format)]

        date_function_kwargs = {'title': table_field.get('title'),
                                'date_format': date_format}

        annotations_value = data_attr.get('annotations_value')
        if annotations_value:
            new_field_name = f'{annotations_value}_{field_name}'
            function = ANNOTATION_VALUE_FUNCTIONS[annotations_value]
            date_function_kwargs['annotations_value'] = {new_field_name: function(field_name)}
            field_name = new_field_name

        date_function_kwargs.update({'field': field_name,
                                     'column_name': field_name})

        field = self.date_field(**date_function_kwargs)
        fields.append(field)
        return field_name

    def get_number_field(self, table_field, fields, totals, col_type_override):
        data_attr = split_attr(table_field)
        field_name = table_field['field']
        css_class = None

        annotations_type = data_attr.get('annotations_type')

        if col_type_override:
            field = copy.deepcopy(col_type_override)
            title = table_field.get('title')
            if annotations_type == 'count':
                new_field_name = f'{annotations_type}_{field_name}'
                number_function_kwargs = {}
                if title:
                    number_function_kwargs['title'] = title
                function = ANNOTATION_FUNCTIONS[annotations_type]
                number_function_kwargs['annotations'] = {new_field_name: function(field.field)}

                number_function_kwargs.update({'field': new_field_name,
                                               'column_name': field_name})
                field = self.number_field(**number_function_kwargs)
            else:
                css_class = field.column_defs.get('className')
                if title:
                    field.title = title
                if annotations_type:
                    new_field_name = f'{annotations_type}_{field_name}'

                    function = ANNOTATION_FUNCTIONS[annotations_type]
                    field.annotations = {new_field_name: function(field.field)}
                    field.field = new_field_name

            fields.append(field)
        else:
            number_function_kwargs = {'title': table_field.get('title')}
            decimal_places = data_attr.get('decimal_places')

            if decimal_places:
                number_function_kwargs = {'decimal_places': int(decimal_places)}

            if annotations_type:
                new_field_name = f'{annotations_type}_{field_name}'
                function = ANNOTATION_FUNCTIONS[annotations_type]
                number_function_kwargs['annotations'] = {new_field_name: function(field_name)}
                field_name = new_field_name

            number_function_kwargs.update({'field': field_name,
                                           'column_name': field_name})

            field = self.number_field(**number_function_kwargs)
            fields.append(field)

        decimal_places = data_attr.get('decimal_places', 0)
        show_total = data_attr.get('show_totals')
        if show_total == '1':
            totals[field_name] = {'sum': 'to_fixed', 'decimal_places': decimal_places, 'css_class': css_class}

        return field_name

    def setup_table(self, table):
        table.extra_filters = self.extra_filters
        table_fields = json.loads(self.table_report.table_fields)

        fields = []
        totals = {}
        base_modal = self.table_report.get_base_modal()
        first_field_name = None
        for table_field in table_fields:
            field = table_field['field']

            django_field, col_type_override, _ = get_django_field(base_modal=base_modal, field=field)

            if isinstance(django_field, DATE_FIELDS):
                field_name = self.get_date_field(table_field=table_field, fields=fields)

            elif isinstance(django_field, NUMBER_FIELDS):
                field_name = self.get_number_field(table_field=table_field,
                                                   fields=fields,
                                                   totals=totals,
                                                   col_type_override=col_type_override)
            else:
                field_attr = {}
                if 'title' in table_field:
                    field_attr['title'] = table_field['title']
                field_name = field
                if field_attr:
                    field = (field, field_attr)
                fields.append(field)
            if not first_field_name:
                first_field_name = field_name
        table.add_columns(*fields)
        table.table_options['pageLength'] = self.table_report.page_length
        table.table_options['bStateSave'] = False

        if totals:
            totals[first_field_name] = {'text': 'Totals'}
            table.add_plugin(ColumnTotals, totals)

    def extra_filters(self, query):
        report_query = self.get_report_query(report=self.table_report)
        if not report_query:
            return query

        return self.process_query_filters(query=query,
                                          search_filter_data=report_query.query)

    def add_to_context(self, **kwargs):
        return {'title': self.get_title(),
                'table_report': self.table_report}

    def setup_menu(self):
        super().setup_menu()
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

        query_id = self.slug.get(f'query{self.table_report.id}')
        slug_str = ''
        if query_id:
            slug_str = f'-query_id-{query_id}'

        return [MenuItem(f'advanced_report_builder:table_modal,pk-{self.table_report.id}{slug_str}',
                         menu_display='Edit',
                         font_awesome='fas fa-pencil-alt', css_classes=['btn-primary'])]

    def queries_menu(self):
        return []


class TableModal(QueryBuilderModalBase):
    size = 'xl'
    model = TableReport
    process = PROCESS_EDIT_DELETE
    permission_delete = PERMISSION_OFF

    form_fields = ['name',
                   ('has_clickable_rows', {'widget': Toggle(attrs={'data-onstyle': 'success',
                                                                   'data-on': 'YES',
                                                                   'data-off': 'NO'})}),
                   'page_length',
                   'report_type',
                   'table_fields',
                   ]

    def __init__(self, *args, **kwargs):
        self.report_query = None
        self.show_query_name = False
        super().__init__(*args, **kwargs)

    def form_setup(self, form, *_args, **_kwargs):
        self.add_query_data(form)

        fields = [FieldEx('name'),
                  FieldEx('report_type'),
                  FieldEx('has_clickable_rows', template='django_modals/fields/label_checkbox.html'),
                  FieldEx('page_length', template='django_modals/fields/label_checkbox.html'),
                  FieldEx('table_fields', template='advanced_report_builder/fields/select_column.html')]

        if self.show_query_name:
            fields.append(FieldEx('query_name'))

        fields.append(FieldEx('query_data', template='advanced_report_builder/fields/query_builder.html'))
        return fields

    def form_valid(self, form):
        table_report = form.save()

        if not self.report_query and form.cleaned_data['query_data']:
            ReportQuery(query=form.cleaned_data['query_data'],
                        report=table_report).save()
        elif form.cleaned_data['query_data']:
            self.report_query.query = form.cleaned_data['query_data']
            if self.show_query_name:
                self.report_query.name = form.cleaned_data['query_name']
            self.report_query.save()
        elif self.report_query:
            self.report_query.delete()

        return self.command_response('reload')

    def _get_fields(self, base_model, fields, tables, report_builder_fields,
                    prefix='', title_prefix='', title=None, colour=None):
        if title is None:
            title = report_builder_fields.title
        if colour is None:
            colour = report_builder_fields.colour

        tables.append({'name': title,
                       'colour': colour})

        for report_builder_field in report_builder_fields.fields:

            column_initialisor = ColumnInitialisor(start_model=base_model, path=report_builder_field)
            columns = column_initialisor.get_columns()
            for column in columns:
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

        report_type = get_object_or_404(ReportType, pk=report_type_id)
        base_model = report_type.content_type.model_class()
        report_builder_fields = getattr(base_model, report_type.report_builder_class_name, None)
        fields = []
        tables = []
        self._get_fields(base_model=base_model,
                         fields=fields,
                         tables=tables,
                         report_builder_fields=report_builder_fields)
        return self.command_response('report_fields', data=json.dumps({'fields': fields,
                                                                       'tables': tables}))


class FieldModal(FormModal):
    form_class = FieldForm

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
        self.add_command({'function': 'save_query_builder'})
        self.add_command({'function': 'update_selection'})
        return self.command_response('close')
