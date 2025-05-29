from ajax_helpers.mixins import AjaxHelpers
from ajax_helpers.utils import is_ajax
from django.conf import settings
from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import TemplateView
from django_menus.menu import MenuItemDisplay, MenuMixin
from django_modals.helper import modal_button, modal_button_method
from django_modals.modals import Modal

from advanced_report_builder.duplicate import DuplicateReport
from advanced_report_builder.models import Report
from advanced_report_builder.utils import split_slug
from advanced_report_builder.views.bar_charts import BarChartView
from advanced_report_builder.views.calendar import CalendarView
from advanced_report_builder.views.datatables.datatables import TableView
from advanced_report_builder.views.funnel_charts import FunnelChartView
from advanced_report_builder.views.kanban import KanbanView
from advanced_report_builder.views.line_charts import LineChartView
from advanced_report_builder.views.pie_charts import PieChartView
from advanced_report_builder.views.single_values import SingleValueView


class ViewReportBase(AjaxHelpers, MenuMixin, TemplateView):
    model = Report
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
    enable_links = True

    custom_views = {}

    views_overrides = {}

    def __init__(self, *args, **kwargs):
        self.report = None
        super().__init__(*args, **kwargs)

    def redirect_url(self):
        """used if the slug changes"""
        return None

    def dispatch(self, request, *args, **kwargs):
        slug = split_slug(self.kwargs['slug'])
        self.report = self.model.objects.filter(slug=slug['pk']).first()

        if self.report is None:
            self.report = self.model.objects.filter(slug_alias=slug['pk']).first()
            if self.report is None:
                return self.report_not_found()
            else:
                redirect_url = self.redirect_url()
                if redirect_url:
                    return redirect_url

        if not self.has_permission():
            return self.report_no_permission()

        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        """You can over override this to check if the user has permission to view the report.
        If return false 'report_no_permission' will be called"""
        return True

    def report_no_permission(self):
        raise Http404

    def report_not_found(self):
        raise Http404

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        view = self.get_view(report=self.report)
        self.kwargs['report'] = self.report
        self.kwargs['enable_links'] = self.enable_links
        report_data = view.as_view()(self.request, *self.args, **self.kwargs).rendered_content
        context['report'] = report_data
        return context

    def get_view(self, report):
        if report.instance_type == 'customreport':
            view_name = report.customreport.view_name
            return self.custom_views.get(view_name)
        elif report.instance_type in self.views_overrides:
            return self.views_overrides.get(report.instance_type)
        return self.views.get(report.instance_type)

    def post(self, request, *args, **kwargs):
        if (
            is_ajax(request)
            and request.content_type
            in [
                'application/json',
                'multipart/form-data',
            ]
            and hasattr(super(), 'post')
        ):
            # noinspection PyUnresolvedReferences
            return super().post(request, *args, **kwargs)

        view = self.get_view(report=self.report)
        self.kwargs['report'] = self.report
        self.kwargs['enable_links'] = self.enable_links
        return view.as_view()(self.request, *self.args, **self.kwargs)


class DuplicateReportModal(Modal):
    menu_display = MenuItemDisplay('Duplicate', font_awesome='fas fa-copy')

    def modal_content(self):
        return 'Are you sure you want to duplicate this report?'

    def get_modal_buttons(self):
        return [
            modal_button_method('Confirm', 'duplicate'),
            modal_button('Cancel', 'close', 'btn-secondary'),
        ]

    def button_duplicate(self, **_kwargs):
        report = get_object_or_404(Report, id=self.slug['pk'])
        duplicate_report = DuplicateReport()
        new_report = duplicate_report.duplicate(report=report)
        messages.add_message(self.request, messages.SUCCESS, f'Successfully duplicated {report.name}')

        url_name = getattr(settings, 'REPORT_BUILDER_DETAIL_URL_NAME', '')
        if url_name:
            url = reverse(url_name, kwargs={'slug': new_report.slug})
            return self.command_response('redirect', url=url)
        else:
            return self.command_response('reload')
