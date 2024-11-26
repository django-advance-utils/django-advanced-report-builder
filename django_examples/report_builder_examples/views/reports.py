from django.shortcuts import redirect
from django_datatables.columns import ColumnLink
from django_menus.menu import MenuItem
from django_modals.modals import ModelFormModal
from django_modals.widgets.widgets import Toggle
from report_builder_examples.views.base import MainMenu, MainIndices
from report_builder_examples.views.custom import Custom1, CustomWithQuery

from advanced_report_builder.models import Report
from advanced_report_builder.views.bar_charts import BarChartView
from advanced_report_builder.views.datatables.datatables import TableView
from advanced_report_builder.views.funnel_charts import FunnelChartView
from advanced_report_builder.views.kanban import KanbanView
from advanced_report_builder.views.line_charts import LineChartView
from advanced_report_builder.views.pie_charts import PieChartView
from advanced_report_builder.views.reports import ViewReportBase
from advanced_report_builder.views.single_values import SingleValueView
from report_builder_examples.models import ReportPermission


class ViewReports(MainIndices):
    model = Report
    table_title = 'Reports'

    def setup_menu(self):
        super().setup_menu()
        self.add_menu('table_menu', 'button_group').add_items(
            MenuItem(menu_display='Add Report', no_hover=True, css_classes='btn-secondary',
                     dropdown=[MenuItem('advanced_report_builder:table_modal,-',
                                        'Table',
                                        font_awesome='fas fa-table'),
                               MenuItem('advanced_report_builder:single_value_modal,-',
                                        'Single Value',
                                        font_awesome='fas fa-box-open'),
                               MenuItem('advanced_report_builder:bar_chart_modal,-',
                                        'Bar Chart',
                                        font_awesome='fas fa-chart-bar'),
                               MenuItem('advanced_report_builder:line_chart_modal,-',
                                        'Line Chart',
                                        font_awesome='fas fa-chart-line'),
                               MenuItem('advanced_report_builder:pie_chart_modal,-',
                                        'Pie Chart',
                                        font_awesome='fas fa-chart-pie'),
                               MenuItem('advanced_report_builder:funnel_chart_modal,-',
                                        'Funnel Chart',
                                        font_awesome='fas fa-filter'),
                               MenuItem('advanced_report_builder:kanban_modal,-',
                                        'Kanban',
                                        font_awesome='fas fa-chart-bar fa-flip-vertical'),
                               MenuItem('advanced_report_builder:calendar_modal,-',
                                        'Calendar',
                                        font_awesome='far fa-calendar'),
                               ]),
        )

    @staticmethod
    def setup_table(table):
        table.add_columns(
            ('id', {'column_defs': {'width': '30px'}}),
            'slug',
            'name',
            'instance_type',
            'OutputTypeIcon',
            'OutputType',
            'version',
            ColumnLink(column_name='view_report',
                       field='name',
                       link_ref_column='slug',
                       url_name='report_builder_examples:view_report'),
        )


class ViewSingleValueReport(SingleValueView):
    def pod_report_menu(self):
        return [('report_builder_examples:index', 'Back', {'css_classes': 'btn-secondary'}),
                *super().pod_report_menu()]


class ViewTableReport(TableView):
    def pod_report_menu(self):
        menu = [('report_builder_examples:index', 'Back', {'css_classes': 'btn-secondary'}),
                *super().pod_report_menu()]
        if hasattr(self.report, 'reportpermission'):
            menu.append((f'report_builder_examples:permission_modal,pk-{self.report.id}',
                         'Permission', {'css_classes': 'btn-danger', 'font_awesome': 'fas fa-key'}))
        else:
            menu.append((f'report_builder_examples:permission_modal,report_id-{self.report.id}',
                         'Permission', {'css_classes': 'btn-danger', 'font_awesome': 'fas fa-key'}))
        return menu


class ViewBarChartReport(BarChartView):
    def pod_report_menu(self):
        return [('report_builder_examples:index', 'Back', {'css_classes': 'btn-secondary'}),
                *super().pod_report_menu()]


class ViewLineChartReport(LineChartView):
    def pod_report_menu(self):
        return [('report_builder_examples:index', 'Back', {'css_classes': 'btn-secondary'}),
                *super().pod_report_menu()]


class ViewPieChartReport(PieChartView):
    def pod_report_menu(self):
        return [('report_builder_examples:index', 'Back', {'css_classes': 'btn-secondary'}),
                *super().pod_report_menu()]


class ViewFunnelChartReport(FunnelChartView):
    def pod_report_menu(self):
        return [('report_builder_examples:index', 'Back', {'css_classes': 'btn-secondary'}),
                *super().pod_report_menu()]


class ViewKanbanViewReport(KanbanView):
    def pod_report_menu(self):
        return [('report_builder_examples:index', 'Back', {'css_classes': 'btn-secondary'}),
                *super().pod_report_menu()]


class ViewReport(MainMenu, ViewReportBase):
    template_name = 'report_builder_examples/report.html'
    views_overrides = {'tablereport': ViewTableReport,
                       'singlevaluereport': ViewSingleValueReport,
                       'barchartreport': ViewBarChartReport,
                       'linechartreport': ViewLineChartReport,
                       'piechartreport': ViewPieChartReport,
                       'funnelchartreport': ViewFunnelChartReport,
                       'kanbanreport': ViewKanbanViewReport,
                       }

    custom_views = {'custom1': Custom1,
                    'custom_with_query': CustomWithQuery}

    def report_not_found(self):
        return redirect('report_builder_examples:index')

    def redirect_url(self):
        return redirect('report_builder_examples:view_report', slug=self.report.slug)

    def has_permission(self):
        report = self.report
        if hasattr(report, 'reportpermission'):
            if report.reportpermission.requires_superuser:
                return self.request.user.is_superuser
        return True


class PermissionModal(ModelFormModal):
    model = ReportPermission
    form_fields = ['requires_superuser']
    widgets = {'requires_superuser': Toggle()}
