from ajax_helpers.mixins import AjaxHelpers
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView
from django_menus.menu import MenuMixin

from advanced_report_builder.models import Report
from advanced_report_builder.utils import split_slug
from advanced_report_builder.views.datatables import TableView
from advanced_report_builder.views.single_values import SingleValueView


class ViewReportBase(AjaxHelpers, MenuMixin, TemplateView):
    model = Report
    views = {'tablereport': TableView,
             'singlevaluereport': SingleValueView}
    views_overrides = {}

    def get_object(self):
        slug = split_slug(self.kwargs['slug'])
        return get_object_or_404(self.model, slug=slug['pk'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        report = self.get_object()
        view = self.get_view(report=report)
        self.kwargs['report'] = report
        report_data = view.as_view()(self.request, *self.args, **self.kwargs).rendered_content
        context['report'] = report_data
        return context

    def get_view(self, report):
        if report.instance_type in self.views_overrides:
            return self.views_overrides.get(report.instance_type)
        return self.views.get(report.instance_type)

    def post(self, request, *args, **kwargs):
        report = self.get_object()
        view = self.get_view(report=report)
        self.kwargs['report'] = report
        return view.as_view()(self.request, *self.args, **self.kwargs)

