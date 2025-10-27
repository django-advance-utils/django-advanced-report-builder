from django.views.generic import TemplateView
from django_menus.menu import MenuItem
from django_modals.modals import ModelFormModal
from django_modals.processes import PROCESS_EDIT_DELETE, PERMISSION_OFF
from django_modals.widgets.select2 import Select2Multiple

from advanced_report_builder.columns import ReportBuilderNumberColumn
from advanced_report_builder.filter_query import FilterQueryMixin
from advanced_report_builder.models import MultiValueReport
from advanced_report_builder.views.report import ReportBase
from advanced_report_builder.widgets import SmallNumberInputWidget


class MultiValueModal(ModelFormModal):
    size = 'xl'
    process = PROCESS_EDIT_DELETE
    permission_delete = PERMISSION_OFF
    model = MultiValueReport
    widgets = {'report_tags': Select2Multiple,
               'rows': SmallNumberInputWidget,
               'columns': SmallNumberInputWidget,}
    ajax_commands = ['datatable', 'button']

    form_fields = ['name',
                   'notes',
                   'report_tags',
                   'rows',
                   'columns']


class MultiValueView(ReportBase, FilterQueryMixin, TemplateView):
    number_field = ReportBuilderNumberColumn
    template_name = 'advanced_report_builder/multi_values/report.html'
    chart_js_table = MultiValueReport

    def __init__(self, *args, **kwargs):
        self.chart_report = None
        super().__init__(*args, **kwargs)

    def setup_menu(self):
        super().setup_menu()
        if self.dashboard_report and self.enable_edit:
            report_menu = self.pod_dashboard_edit_menu()
        elif self.dashboard_report and not self.enable_edit:
            report_menu = self.pod_dashboard_view_menu()
        else:
            report_menu = self.pod_report_menu()
        self.add_menu('button_menu', 'button_group').add_items(
            *report_menu,
            *self.queries_menu(report=self.report, dashboard_report=self.dashboard_report),
        )

    def dispatch(self, request, *args, **kwargs):
        self.report = kwargs.get('report')
        self.chart_report = self.report.multivaluereport
        self.dashboard_report = kwargs.get('dashboard_report')
        self.enable_edit = kwargs.get('enable_edit')
        return super().dispatch(request, *args, **kwargs)

    def pod_dashboard_view_menu(self):
        return []

    def pod_report_menu(self):
        return [
            MenuItem(
                f'advanced_report_builder:multi_value_modal,pk-{self.chart_report.id}',
                menu_display='Edit',
                font_awesome='fas fa-pencil-alt',
                css_classes=['btn-primary'],
            ),
            *self.duplicate_menu(request=self.request, report_id=self.chart_report.id),
        ]

    def pod_dashboard_edit_menu(self):
        return [
            MenuItem(
                f'advanced_report_builder:dashboard_report_modal,pk-{self.dashboard_report.id}',
                menu_display='Edit',
                font_awesome='fas fa-pencil-alt',
                css_classes=['btn-primary'],
            )
        ]