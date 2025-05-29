import copy

from ajax_helpers.mixins import AjaxHelpers
from django.conf import settings
from django.forms import ChoiceField, ModelChoiceField
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import TemplateView
from django_menus.menu import MenuMixin
from django_modals.forms import CrispyForm
from django_modals.modals import FormModal, ModelFormModal
from django_modals.processes import (
    PERMISSION_DISABLE,
    PERMISSION_OFF,
    PROCESS_EDIT_DELETE,
)
from django_modals.widgets.select2 import Select2
from django_modals.widgets.widgets import Toggle

from advanced_report_builder.globals import CALENDAR_VIEW_TYPE_CHOICES
from advanced_report_builder.models import (
    Dashboard,
    DashboardReport,
    Report,
    ReportQuery,
)
from advanced_report_builder.utils import split_slug
from advanced_report_builder.views.bar_charts import BarChartView
from advanced_report_builder.views.calendar import CalendarView
from advanced_report_builder.views.datatables.datatables import TableView
from advanced_report_builder.views.funnel_charts import FunnelChartView
from advanced_report_builder.views.kanban import KanbanView
from advanced_report_builder.views.line_charts import LineChartView
from advanced_report_builder.views.pie_charts import PieChartView
from advanced_report_builder.views.single_values import SingleValueView


class ViewDashboardBase(AjaxHelpers, MenuMixin, TemplateView):
    model = Dashboard
    enable_edit = True
    enable_links = True
    views = {
        'tablereport': TableView,
        'singlevaluereport': SingleValueView,
        'barchartreport': BarChartView,
        'linechartreport': LineChartView,
        'piechartreport': PieChartView,
        'funnelchartreport': FunnelChartView,
        'kanbanreport': KanbanView,
        'calendarreport': CalendarView,
    }

    custom_views = {}
    views_overrides = {}
    ajax_commands = ['button', 'select2', 'ajax']

    def __init__(self, *args, **kwargs):
        self.dashboard = None
        super().__init__(*args, **kwargs)

    def redirect_url(self):
        """used if the slug changes"""
        return None

    def dashboard_not_found(self):
        raise Http404

    def dispatch(self, request, *args, **kwargs):
        slug = split_slug(self.kwargs['slug'])
        self.dashboard = self.model.objects.filter(slug=slug['pk']).first()

        if self.dashboard is None:
            self.dashboard = self.model.objects.filter(slug_alias=slug['pk']).first()
            if self.dashboard is None:
                return self.dashboard_not_found()
            else:
                redirect_url = self.redirect_url()
                if redirect_url:
                    return redirect_url

        return super().dispatch(request, *args, **kwargs)

    @staticmethod
    def get_top_report_class(reports):
        reports_len = len(reports)
        spans = {
            1: ' col-12',
            2: ' col-12 col-sm-12 col-md-6',
            3: ' col-12 col-sm-12 col-md-4',
            4: ' col-12 col-sm-12 col-md-6 col-lg-3',
            6: ' col-12 col-sm-12 col-md-4',
            9: ' col-12 col-sm-12 col-md-4',
        }
        return spans.get(reports_len, ' col-12 col-sm-12 col-md-3')

    def has_dashboard_permission(self):
        """You can over override this to check if the user has permission to view the dashboard.
        If return false 'dashboard_no_permission' will be called"""
        return True

    def dashboard_no_permission(self):
        raise Http404

    def has_report_got_permission(self, report):
        """You can over override this to check if the user has permission to view the report.
        If return false 'report_no_permission' will be called"""
        return True

    def report_no_permission(self, dashboard_report, reports):
        pass

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dashboard'] = self.dashboard

        if not self.has_dashboard_permission():
            return self.dashboard_no_permission()

        top_reports = []
        reports = []
        for dashboard_report in self.dashboard.dashboardreport_set.all():
            if self.has_report_got_permission(report=dashboard_report.report):
                report_view = self.get_view(report=dashboard_report.report)
                extra_class_name = report_view().get_dashboard_class(report=dashboard_report.report)
                report_data = self.call_view(
                    dashboard_report=dashboard_report, report_view=report_view
                ).rendered_content
                report = {
                    'render': report_data,
                    'name': dashboard_report.report.name,
                    'id': dashboard_report.id,
                    'class': dashboard_report.get_class(extra_class_name=extra_class_name),
                }
                if dashboard_report.top:
                    top_reports.append(report)
                else:
                    reports.append(report)
            else:
                self.report_no_permission(dashboard_report=dashboard_report, reports=reports)
        context['top_reports'] = top_reports
        context['top_reports_class'] = self.get_top_report_class(top_reports)

        context['reports'] = reports
        context['enable_edit'] = self.enable_edit
        return context

    def get_view(self, report):
        if report.instance_type == 'customreport':
            view_name = report.customreport.view_name
            return self.custom_views.get(view_name)
        elif report.instance_type in self.views_overrides:
            return self.views_overrides.get(report.instance_type)
        return self.views.get(report.instance_type)

    def call_view(self, dashboard_report, report_view=None):
        if report_view is None:
            report_view = self.get_view(report=dashboard_report.report)
        view_kwargs = copy.deepcopy(self.kwargs)
        view_kwargs['report'] = dashboard_report.report
        view_kwargs['dashboard_report'] = dashboard_report
        view_kwargs['enable_edit'] = self.enable_edit
        view_kwargs['enable_links'] = self.enable_links

        return report_view.as_view()(self.request, *self.args, **view_kwargs)

    def post(self, request, *args, **kwargs):
        table_id = request.POST.get('table_id')
        if table_id:  # must be a datatable:
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
    form_fields = ['name', 'display_option']
    process = PROCESS_EDIT_DELETE
    permission_delete = PERMISSION_OFF

    def post_save(self, created, form):
        if created:
            url_name = getattr(settings, 'REPORT_BUILDER_DASHBOARD_URL_NAME', '')
            if url_name:
                url = reverse(url_name, kwargs={'slug': self.object.slug})
                self.add_command('redirect', url=url)


class DashboardReportModal(ModelFormModal):
    model = DashboardReport
    process = PROCESS_EDIT_DELETE
    permission_delete = PERMISSION_OFF
    permission_create = PERMISSION_DISABLE

    @property
    def form_fields(self):
        fields = ['name_override', 'top', 'display_option']
        if self.object.report.instance_type != 'calendarreport':
            fields += [
                'show_versions',
                'report_query',
            ]
        return fields

    widgets = {
        'top': Toggle(attrs={'data-onstyle': 'success', 'data-on': 'YES', 'data-off': 'NO'}),
        'show_versions': Toggle(attrs={'data-onstyle': 'success', 'data-on': 'YES', 'data-off': 'NO'}),
    }

    def form_setup(self, form, *_args, **_kwargs):
        form.add_trigger(
            'top',
            'onchange',
            [
                {
                    'selector': '#div_id_display_option',
                    'values': {'checked': 'hide'},
                    'default': 'show',
                },
            ],
        )
        if self.object.report.instance_type == 'calendarreport':
            view_type = self.object.report.calendarreport.get_view_type_display()
            choices = [(0, f'Default ({view_type})'), *CALENDAR_VIEW_TYPE_CHOICES]
            calendar_view_type = self.object.options.get('calendar_view_type') if self.object.options else None
            form.fields['calendar_view_type'] = ChoiceField(
                choices=choices, required=False, widget=Select2(), initial=calendar_view_type
            )
        else:
            report_queries = ReportQuery.objects.filter(report=form.instance.report)
            form.fields['report_query'] = ModelChoiceField(queryset=report_queries, widget=Select2, required=False)

    def form_valid(self, form):
        instance = form.save(commit=False)
        instance._current_user = self.request.user
        if instance.report.instance_type == 'calendarreport':
            options = {'calendar_view_type': form.cleaned_data['calendar_view_type']}
            instance.options = options
        instance.save()
        return self.command_response('reload')


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
