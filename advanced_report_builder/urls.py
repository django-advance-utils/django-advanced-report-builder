from django.urls import path

from advanced_report_builder.views.bar_charts import (
    BarChartBreakdownFieldModal,
    BarChartFieldModal,
    BarChartModal,
    BarChartShowBreakdownModal,
)
from advanced_report_builder.views.calendar import (
    CalendarDataSetDuplicateModal,
    CalendarDataSetModal,
    CalendarDescriptionDuplicateModal,
    CalendarDescriptionModal,
    CalendarModal,
)
from advanced_report_builder.views.custom import CustomModal
from advanced_report_builder.views.dashboard import (
    DashboardAddReportModal,
    DashboardModal,
    DashboardReportModal,
)
from advanced_report_builder.views.datatables.modal import (
    TableFieldModal,
    TableModal,
    TablePivotModal,
)
from advanced_report_builder.views.funnel_charts import (
    FunnelChartFieldModal,
    FunnelChartModal,
)
from advanced_report_builder.views.kanban import (
    KanbanDescriptionDuplicateModal,
    KanbanDescriptionModal,
    KanbanLaneDuplicateModal,
    KanbanLaneModal,
    KanbanModal,
)
from advanced_report_builder.views.line_charts import (
    LineChartFieldModal,
    LineChartModal,
)
from advanced_report_builder.views.pie_charts import PieChartFieldModal, PieChartModal
from advanced_report_builder.views.query_modal.modal import QueryModal, QueryOrderModal
from advanced_report_builder.views.reports import DuplicateReportModal
from advanced_report_builder.views.single_values import (
    QueryNumeratorModal,
    SingleValueModal,
    SingleValueShowBreakdownModal,
    SingleValueTableFieldModal,
)
from advanced_report_builder.views.targets.views import TargetModal

app_name = 'advanced_report_builder'


urlpatterns = [
    path('query/modal/query/<str:slug>', QueryModal.as_view(), name='query_modal'),
    path(
        'query/modal/query/order/<str:slug>',
        QueryOrderModal.as_view(),
        name='query_order_modal',
    ),
    path('table/modal/<str:slug>/', TableModal.as_view(), name='table_modal'),
    path(
        'table/modal/field/<str:slug>/',
        TableFieldModal.as_view(),
        name='table_field_modal',
    ),
    path(
        'table/modal/pivot/<str:slug>/',
        TablePivotModal.as_view(),
        name='table_pivot_modal',
    ),
    path(
        'single-value/modal/<str:slug>/',
        SingleValueModal.as_view(),
        name='single_value_modal',
    ),
    path(
        'single-value/modal/field/<str:slug>/',
        SingleValueTableFieldModal.as_view(),
        name='single_value_field_modal',
    ),
    path(
        'single-value/modal/numerator-field/<str:slug>/',
        QueryNumeratorModal.as_view(),
        name='single_value_numerator_modal',
    ),
    path(
        'single-value/show-breakdown/<str:slug>/',
        SingleValueShowBreakdownModal.as_view(),
        name='single_value_show_breakdown_modal',
    ),
    path('bar-chart/modal/<str:slug>/', BarChartModal.as_view(), name='bar_chart_modal'),
    path(
        'bar-chart/modal/field/<str:slug>/',
        BarChartFieldModal.as_view(),
        name='bar_chart_field_modal',
    ),
    path(
        'bar-chart/modal/breakdown/field/<str:slug>/',
        BarChartBreakdownFieldModal.as_view(),
        name='bar_chart_breakdown_field_modal',
    ),
    path(
        'bar-chart/show-breakdown/<str:slug>/',
        BarChartShowBreakdownModal.as_view(),
        name='bar_chart_show_breakdown_modal',
    ),
    path(
        'line-chart/modal/<str:slug>/',
        LineChartModal.as_view(),
        name='line_chart_modal',
    ),
    path(
        'line-chart/modal/field/<str:slug>/',
        LineChartFieldModal.as_view(),
        name='line_chart_field_modal',
    ),
    path('pie-chart/modal/<str:slug>/', PieChartModal.as_view(), name='pie_chart_modal'),
    path(
        'pie-chart/modal/field/<str:slug>/',
        PieChartFieldModal.as_view(),
        name='pie_chart_field_modal',
    ),
    path(
        'funnel-chart/modal/<str:slug>/',
        FunnelChartModal.as_view(),
        name='funnel_chart_modal',
    ),
    path(
        'funnel-chart/modal/field/<str:slug>/',
        FunnelChartFieldModal.as_view(),
        name='funnel_chart_field_modal',
    ),
    path('kanban/modal/<str:slug>/', KanbanModal.as_view(), name='kanban_modal'),
    path(
        'kanban/modal/lane/<str:slug>/',
        KanbanLaneModal.as_view(),
        name='kanban_lane_modal',
    ),
    path(
        'kanban/modal/lane/duplicate/<str:slug>/',
        KanbanLaneDuplicateModal.as_view(),
        name='kanban_lane_duplicate_modal',
    ),
    path(
        'kanban/modal/description/<str:slug>/',
        KanbanDescriptionModal.as_view(),
        name='kanban_description_modal',
    ),
    path(
        'kanban/modal/description/duplicate/<str:slug>/',
        KanbanDescriptionDuplicateModal.as_view(),
        name='kanban_description_duplicate_modal',
    ),
    path('calendar/modal/<str:slug>/', CalendarModal.as_view(), name='calendar_modal'),
    path('calendar/modal/data-set/<str:slug>/', CalendarDataSetModal.as_view(), name='calendar_data_set_modal'),
    path(
        'calendar/modal/lane/duplicate/<str:slug>/',
        CalendarDataSetDuplicateModal.as_view(),
        name='calendar_data_set_duplicate_modal',
    ),
    path(
        'calendar/modal/description/<str:slug>/', CalendarDescriptionModal.as_view(), name='calendar_description_modal'
    ),
    path(
        'calendar/modal/description/duplicate/<str:slug>/',
        CalendarDescriptionDuplicateModal.as_view(),
        name='calendar_description_duplicate_modal',
    ),
    path('custom/modal/<str:slug>/', CustomModal.as_view(), name='custom_modal'),
    path(
        'dashboard/report/<str:slug>/',
        DashboardReportModal.as_view(),
        name='dashboard_report_modal',
    ),
    path('dashboard/<str:slug>/', DashboardModal.as_view(), name='dashboard_modal'),
    path(
        'dashboard/add/<str:slug>/',
        DashboardAddReportModal.as_view(),
        name='add_dashboard_report',
    ),
    path(
        'duplicate/<str:slug>/',
        DuplicateReportModal.as_view(),
        name='duplicate_report_modal',
    ),
    path('target/modal/<str:slug>/', TargetModal.as_view(), name='target_modal'),
]
