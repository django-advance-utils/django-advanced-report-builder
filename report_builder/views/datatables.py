import json

from ajax_helpers.mixins import AjaxHelpers
from django.shortcuts import get_object_or_404
from django_datatables.datatables import DatatableView
from django_menus.menu import MenuMixin, MenuItem
from django_modals.fields import FieldEx
from django_modals.modals import ModelFormModal
from django_modals.widgets.widgets import Toggle

from report_builder.models import TableReport


class TableView(AjaxHelpers, MenuMixin, DatatableView):
    template_name = 'report_builder/datatable.html'

    def add_tables(self):
        return None

    def dispatch(self, request, *args, **kwargs):
        self.table_report = get_object_or_404(TableReport, pk=self.kwargs['pk'])
        base_model = self.table_report.report_type.content_type.model_class()
        self.add_table(type(self).__name__.lower(), model=base_model)

        return super().dispatch(request, *args, **kwargs)

    def setup_table(self, table):
        fields = self.table_report.get_field_strings()
        table.add_columns(*fields)

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


class TableModal(ModelFormModal):
    size = 'xl'
    model = TableReport
    ajax_commands = ['button', 'select2', 'ajax']
    form_fields = ['name',
                   ('has_clickable_rows', {'widget': Toggle(attrs={'data-onstyle': 'success',
                                                                   'data-on': 'YES',
                                                                   'data-off': 'NO'})}),
                   'report_type',
                   'table_fields'
                   ]

    def form_setup(self, form, *_args, **_kwargs):
        return [FieldEx('name'),
                FieldEx('report_type'),
                FieldEx('has_clickable_rows', template='django_modals/fields/label_checkbox.html'),
                FieldEx('table_fields', template='report_builder/fields/select_column.html'),
                ]

    def ajax_get_fields(self, **kwargs):
        return self.command_response('report_fields', data=json.dumps({'fields': [{'field': 'name',
                                                                                   'label': 'Name'}]}))
