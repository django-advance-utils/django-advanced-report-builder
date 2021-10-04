from ajax_helpers.mixins import AjaxHelpers
from django.views.generic import DetailView
from django_menus.menu import MenuMixin

from report_builder import OUTPUT_TYPE_TABLE
from report_builder.views.datatables import DatatableReportView


class ViewReportBase(AjaxHelpers, DatatableReportView, MenuMixin, DetailView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        report_data = self.view_report()
        context['report'] = report_data
        return context

    def view_report(self):
        if self.object.output_type == OUTPUT_TYPE_TABLE:
            return self.view_datatable()
        return None

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.output_type == OUTPUT_TYPE_TABLE:
            return self.post_datatable(request, *args, **kwargs)
        return None

    def report_menu(self):
        return []


