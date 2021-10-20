import json

from ajax_helpers.mixins import AjaxHelpers
from crispy_forms.bootstrap import StrictButton
from django.apps import apps

from django.shortcuts import get_object_or_404
from django_datatables.datatables import DatatableView, ColumnInitialisor
from django_menus.menu import MenuMixin, MenuItem
from django_modals.fields import FieldEx
from django_modals.forms import ModelCrispyForm
from django_modals.modals import ModelFormModal, FormModal
from django_modals.widgets.widgets import Toggle

from report_builder.field_types import FieldTypes
from report_builder.filter_query import FilterQueryMixin
from report_builder.forms import FieldForm
from report_builder.models import TableReport, ReportType


class TableView(AjaxHelpers, FilterQueryMixin, MenuMixin, DatatableView):
    template_name = 'report_builder/datatable.html'

    def add_tables(self):
        return None

    def dispatch(self, request, *args, **kwargs):
        self.table_report = get_object_or_404(TableReport, pk=self.kwargs['pk'])
        base_model = self.table_report.report_type.content_type.model_class()
        self.add_table(type(self).__name__.lower(), model=base_model)
        return super().dispatch(request, *args, **kwargs)

    def setup_table(self, table):
        table.extra_filters = self.extra_filters

        fields = self.table_report.get_field_strings()
        table.add_columns(*fields)

    def extra_filters(self, query):
        return self.process_filters(query=query,
                                    search_filter_data=self.table_report.search_filter_data)

    def add_to_context(self, **kwargs):
        return {'table_report': self.table_report}

    def setup_menu(self):
        super().setup_menu()
        self.add_menu('button_menu', 'button_group').add_items(
            *self.pod_menu()
        )

    def pod_menu(self):
        return [MenuItem(f'report_builder:table_modal,pk-{self.table_report.id}',
                         menu_display='Edit',
                         font_awesome='fas fa-pencil-alt', css_classes=['btn-primary'])]


class ReportBaseForm(ModelCrispyForm):
    submit_class = 'btn-success modal-submit'

    def submit_button(self, css_class=submit_class, button_text='Submit'):
        return StrictButton(button_text, css_class=css_class)


class TableModal(ModelFormModal):
    size = 'xl'
    model = TableReport
    base_form = ReportBaseForm
    ajax_commands = ['button', 'select2', 'ajax']
    form_fields = ['name',
                   ('has_clickable_rows', {'widget': Toggle(attrs={'data-onstyle': 'success',
                                                                   'data-on': 'YES',
                                                                   'data-off': 'NO'})}),
                   'report_type',
                   'table_fields',
                   'search_filter_data'

                   ]

    def form_setup(self, form, *_args, **_kwargs):
        return [FieldEx('name'),
                FieldEx('report_type'),
                FieldEx('has_clickable_rows', template='django_modals/fields/label_checkbox.html'),
                FieldEx('table_fields', template='report_builder/fields/select_column.html'),
                FieldEx('search_filter_data', template='report_builder/fields/query_builder.html'),
                ]

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

    def _get_query_builder_fields(self, base_model, query_builder_filters, report_builder_fields, prefix='',
                                  title_prefix=''):

        field_types = FieldTypes()

        for report_builder_field in report_builder_fields.fields:

            column_initialisor = ColumnInitialisor(start_model=base_model, path=report_builder_field)
            columns = column_initialisor.get_columns()
            for column in columns:
                if column_initialisor.django_field is not None:
                    field_types.get_filter(query_builder_filters=query_builder_filters,
                                           django_field=column_initialisor.django_field,
                                           field=prefix + column.column_name,
                                           title=title_prefix + column.title)
        for include in report_builder_fields.includes:
            app_label, model, report_builder_fields_str = include['model'].split('.')
            new_model = apps.get_model(app_label, model)
            new_report_builder_fields = getattr(new_model, report_builder_fields_str, None)
            foreign_key_field = getattr(base_model, include['field'], None).field
            if foreign_key_field.null:
                field_types.get_foreign_key_null_field(query_builder_filters=query_builder_filters,
                                                       field=prefix + include['field'],
                                                       title=title_prefix + include['title'])

            self._get_query_builder_fields(base_model=new_model,
                                           query_builder_filters=query_builder_filters,
                                           report_builder_fields=new_report_builder_fields,
                                           prefix=f"{include['field']}__",
                                           title_prefix=f"{include['title']} --> ")

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

    def ajax_get_query_builder_fields(self, **kwargs):
        report_type_id = kwargs['report_type'][0]
        report_type = get_object_or_404(ReportType, pk=report_type_id)
        base_model = report_type.content_type.model_class()
        report_builder_fields = getattr(base_model, report_type.report_builder_class_name, None)
        query_builder_filters = []
        self._get_query_builder_fields(base_model=base_model,
                                       query_builder_filters=query_builder_filters,
                                       report_builder_fields=report_builder_fields)

        return self.command_response('query_builder', data=json.dumps(query_builder_filters))


class FieldModal(FormModal):
    form_class = FieldForm
    modal_title = 'CHANGE ME'

    def form_valid(self, form):
        selector = self.slug['selector']
        self.add_command({'function': 'html', 'selector': f'#{selector} span', 'html': form.cleaned_data['title']})
        self.add_command({'function': 'save_query_builder'})
        self.add_command({'function': 'update_selection'})
        return self.command_response('close')





