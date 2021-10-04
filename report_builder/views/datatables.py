import json

from django.http import HttpResponse
from django.template.loader import render_to_string
from django_datatables.datatables import DatatableTable
from django_menus.menu import HtmlMenu


class DatatableReportView:

    datatable_template = 'report_builder/datatable.html'

    def __init__(self, *args, **kwargs):
        self.object = None
        super().__init__(*args, **kwargs)
        self.datatables = {}

    def add_datatable(self):
        table_id = f'setup_report{self.object.id}'
        base_model = self.object.report_type.content_type.model_class()
        self.datatables[table_id] = DatatableTable(table_id, model=base_model)
        return self.datatables[table_id]

    def view_datatable(self):
        table = self.add_datatable()
        table_report = self.setup_datatable(table)
        datatable = self.datatables[list(self.datatables.keys())[0]]

        menu = HtmlMenu(self.request, 'button_group').add_items(*self.report_menu())

        return render_to_string(self.datatable_template, {'datatable': datatable,
                                                          'table_report': table_report,
                                                          'menu': menu})

    def setup_datatable(self, table):
        model_name = self.object.get_model_name()
        table_report = getattr(self.object, f"{model_name}tablereport")

        fields = table_report.get_field_strings()
        table.add_columns(*fields)
        return table_report

    @staticmethod
    def get_datatable_query(table, **kwargs):
        return table.get_query(**kwargs)

    def post_datatable(self, request, *args, **kwargs):
        if request.POST.get('datatable_data'):
            # table = self.datatables[request.POST['table_id']]
            table = self.add_datatable()
            self.setup_datatable(table=table)
            results = self.get_datatable_query(table, **kwargs)
            return HttpResponse(table.get_json(request, results), content_type='application/json')
        if hasattr(super(), 'post'):
            # noinspection PyUnresolvedReferences
            return super().post(request, *args, **kwargs)
        elif request.is_ajax() and request.content_type == 'application/json':
            response = json.loads(request.body)
            raise Exception(f'May need to use AjaxHelpers Mixin or'
                            f' add one of these \n{", ".join(response.keys())}\nto ajax_commands ')
