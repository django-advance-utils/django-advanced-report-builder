from django.views.generic import DetailView

from report_builder import OUTPUT_TYPE_TABLE
from report_builder.views.datatables import DatatableReportView


class ViewReportBase(DatatableReportView, DetailView):
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

