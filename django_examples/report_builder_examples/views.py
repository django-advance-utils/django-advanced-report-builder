from django.shortcuts import get_object_or_404
from django_datatables.datatables import DatatableView, DatatableTable

from django_menus.menu import MenuMixin
from django.apps import apps


class MainMenu(MenuMixin):

    def setup_menu(self):
        super().setup_menu()
        self.add_menu('main_menu').add_items('ajax_main')


class DatatableReportView(DatatableView):
    template_name = 'report_builder_examples/datatable.html'

    def add_table(self, table_id, **kwargs):
        model_name = 'Report'
        table_report_cls = apps.get_model(app_label='report_builder_examples', model_name=f'{model_name}TableReport')
        self.table_report = get_object_or_404(table_report_cls, pk=1)
        model_name = self.table_report.report_type.content_type.model_class()
        self.tables[table_id] = DatatableTable(table_id, table_options=self.table_options,
                                               table_classes=self.table_classes,
                                               model=model_name)

    def setup_table(self, table):
        fields = self.table_report.get_field_strings()
        table.add_columns(*fields)
