import copy

from ajax_helpers.mixins import AjaxHelpers
from django.http import Http404
from django.views.generic import TemplateView
from django_menus.menu import MenuMixin

from advanced_report_builder.models import Dashboard
from advanced_report_builder.utils import split_slug
from advanced_report_builder.views.datatables import TableView
from advanced_report_builder.views.single_values import SingleValueView


class ViewDashboardBase(AjaxHelpers, MenuMixin, TemplateView):
    model = Dashboard
    views = {'tablereport': TableView,
             'singlevaluereport': SingleValueView}
    views_overrides = {}

    def __init__(self, *args, **kwargs):
        self.dashboard = None
        super().__init__(*args, **kwargs)

    def redirect_url(self):
        """ used if the slug changes"""
        return None

    def dispatch(self, request, *args, **kwargs):
        slug = split_slug(self.kwargs['slug'])
        self.dashboard = self.model.objects.filter(slug=slug['pk']).first()

        if self.dashboard is None:
            self.dashboard = self.model.objects.filter(slug_alias=slug['pk']).first()
            if self.dashboard is None:
                raise Http404
            else:
                redirect_url = self.redirect_url()
                if redirect_url:
                    return redirect_url

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dashboard'] = self.dashboard
        reports = []
        for dashboard_report in self.dashboard.dashboardreport_set.all():
            report_data = self.call_view(report=dashboard_report.report,
                                         dashboard_report_id=dashboard_report.id).rendered_content
            report = {'render': report_data, 'name': dashboard_report.report.name}
            reports.append(report)
        context['reports'] = reports
        return context

    def get_view(self, report):
        if report.instance_type in self.views_overrides:
            return self.views_overrides.get(report.instance_type)
        return self.views.get(report.instance_type)

    def call_view(self, report, dashboard_report_id):
        view = self.get_view(report=report)
        view_kwargs = copy.deepcopy(self.kwargs)
        view_kwargs['report'] = report
        view_kwargs['dashboard_report_id'] = dashboard_report_id
        return view.as_view()(self.request, *self.args, **view_kwargs)

    def post(self, request, *args, **kwargs):
        table_id = request.POST.get('table_id')
        if table_id:   # must be a datatable:
            dashboard_report_id = table_id.split('_')[1]
            if dashboard_report_id:
                dashboard_report = self.dashboard.dashboardreport_set.filter(id=dashboard_report_id).first()

                return self.call_view(report=dashboard_report.report,
                                      dashboard_report_id=dashboard_report.id)

        return super().post(request, *args, **kwargs)
