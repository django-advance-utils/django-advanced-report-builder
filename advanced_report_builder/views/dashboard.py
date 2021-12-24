import copy

from ajax_helpers.mixins import AjaxHelpers
from django.forms import ModelChoiceField
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView
from django_menus.menu import MenuMixin
from django_modals.forms import CrispyForm
from django_modals.modals import ModelFormModal, FormModal
from django_modals.processes import PROCESS_EDIT_DELETE, PERMISSION_OFF
from django_modals.widgets.select2 import Select2
from django_modals.widgets.widgets import Toggle

from advanced_report_builder.models import Dashboard, DashboardReport, Report
from advanced_report_builder.utils import split_slug
from advanced_report_builder.views.bar_charts import BarChartView
from advanced_report_builder.views.datatables import TableView
from advanced_report_builder.views.funnel_charts import FunnelChartView
from advanced_report_builder.views.line_charts import LineChartView
from advanced_report_builder.views.pie_charts import PieChartView
from advanced_report_builder.views.single_values import SingleValueView


class ViewDashboardBase(AjaxHelpers, MenuMixin, TemplateView):
    model = Dashboard
    enable_edit = True
    views = {'tablereport': TableView,
             'singlevaluereport': SingleValueView,
             'barchartreport': BarChartView,
             'linechartreport': LineChartView,
             'piechartreport': PieChartView,
             'funnelchartreport': FunnelChartView,
             }
    views_overrides = {}
    ajax_commands = ['button', 'select2', 'ajax']

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

    @staticmethod
    def get_top_report_class(reports):
        reports_len = len(reports)
        spans = {1: ' col-12',
                 2: ' col-12 col-sm-12 col-md-6',
                 3: ' col-12 col-sm-12 col-md-4',
                 4: ' col-12 col-sm-12 col-md-6 col-lg-3',
                 9: ' col-12 col-sm-12 col-md-4'}
        return spans.get(reports_len, ' col-3 col-sm-12')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dashboard'] = self.dashboard

        top_reports = []
        reports = []

        for dashboard_report in self.dashboard.dashboardreport_set.all():
            report_data = self.call_view(dashboard_report=dashboard_report).rendered_content
            report = {'render': report_data,
                      'name': dashboard_report.report.name,
                      'id': dashboard_report.id,
                      'class': dashboard_report.get_class()}
            if dashboard_report.top:
                top_reports.append(report)
            else:
                reports.append(report)
        context['top_reports'] = top_reports
        context['top_reports_class'] = self.get_top_report_class(top_reports)
        context['reports'] = reports
        return context

    def get_view(self, report):
        if report.instance_type in self.views_overrides:
            return self.views_overrides.get(report.instance_type)
        return self.views.get(report.instance_type)

    def call_view(self, dashboard_report):
        view = self.get_view(report=dashboard_report.report)
        view_kwargs = copy.deepcopy(self.kwargs)
        view_kwargs['report'] = dashboard_report.report
        view_kwargs['dashboard_report'] = dashboard_report
        view_kwargs['enable_edit'] = self.enable_edit
        return view.as_view()(self.request, *self.args, **view_kwargs)

    def post(self, request, *args, **kwargs):
        table_id = request.POST.get('table_id')
        if table_id:   # must be a datatable:
            dashboard_report_id = table_id.split('_')[1]
            if dashboard_report_id:
                dashboard_report = self.dashboard.dashboardreport_set.filter(id=dashboard_report_id).first()
                return self.call_view(dashboard_report=dashboard_report)

        return super().post(request, *args, **kwargs)

    def ajax_change_placement(self, **kwargs):

        ids = kwargs['ids']
        dashboard_reports = DashboardReport.objects.filter(id__in=ids)
        obj_dict = dict([(obj.id, obj) for obj in dashboard_reports])
        sorted_objects = [obj_dict[_id] for _id in ids]

        for index, dashboard_report in enumerate(sorted_objects):
            if dashboard_report.order != index:
                dashboard_report.order = index
                dashboard_report.save()

        return self.command_response()


class DashboardModal(ModelFormModal):
    model = Dashboard
    form_fields = ['name',
                   'display_option']


class DashboardReportModal(ModelFormModal):
    model = DashboardReport
    process = PROCESS_EDIT_DELETE
    permission_delete = PERMISSION_OFF

    form_fields = ['name_override',
                   'top',
                   'display_option']
    widgets = {'top': Toggle(attrs={'data-onstyle': 'success', 'data-on': 'YES', 'data-off': 'NO'})}

    @staticmethod
    def form_setup(form, *_args, **_kwargs):
        form.add_trigger('top', 'onchange', [
            {'selector': '#div_id_display_option', 'values': {'checked': 'hide'}, 'default': 'show'},
        ])


class DashboardAddReportForm(CrispyForm):
    report = ModelChoiceField(queryset=Report.objects.all(), widget=Select2)


class DashboardAddReportModal(FormModal):
    form_class = DashboardAddReportForm
    modal_title = 'Add Report'

    def form_valid(self, form):
        dashboard = get_object_or_404(Dashboard, id=self.slug['pk'])
        dashboard_report = DashboardReport(dashboard=dashboard)
        dashboard_report.report = form.cleaned_data['report']
        dashboard_report.save()
        return self.command_response('reload')
