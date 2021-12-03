from ajax_helpers.mixins import AjaxHelpers
from django.http import Http404
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

    def __init__(self, *args, **kwargs):
        self.report = None
        super().__init__(*args, **kwargs)

    def redirect_url(self):
        """ used if the slug changes"""
        return None

    def dispatch(self, request, *args, **kwargs):
        slug = split_slug(self.kwargs['slug'])
        self.report = self.model.objects.filter(slug=slug['pk']).first()

        if self.report is None:
            self.report = self.model.objects.filter(slug_alias=slug['pk']).first()
            if self.report is None:
                raise Http404
            else:
                redirect_url = self.redirect_url()
                if redirect_url:
                    return redirect_url

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        view = self.get_view(report=self.report)
        self.kwargs['report'] = self.report
        report_data = view.as_view()(self.request, *self.args, **self.kwargs).rendered_content
        context['report'] = report_data
        return context

    def get_view(self, report):
        if report.instance_type in self.views_overrides:
            return self.views_overrides.get(report.instance_type)
        return self.views.get(report.instance_type)

    def post(self, request, *args, **kwargs):
        view = self.get_view(report=self.report)
        self.kwargs['report'] = self.report
        return view.as_view()(self.request, *self.args, **self.kwargs)

