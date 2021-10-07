from ajax_helpers.mixins import AjaxHelpers
from django.views.generic import DetailView
from django_menus.menu import MenuMixin

from report_builder.models import Report
from report_builder.views.datatables import TableView


class ViewReportBase(AjaxHelpers, MenuMixin, DetailView):
    model = Report
    views = {'tablereport': TableView}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        view = self.get_view(report=self.object)
        report_data = view.as_view()(self.request, *self.args, **self.kwargs).rendered_content
        context['report'] = report_data
        return context

    def get_view(self, report):
        return self.views.get(report.instance_type)

    def post(self, request, *args, **kwargs):
        view = self.get_view(report=self.get_object())
        return view.as_view()(self.request, *self.args, **self.kwargs)

