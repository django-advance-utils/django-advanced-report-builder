from advanced_report_builder.views.bar_charts import BarChartView
from advanced_report_builder.views.calendar import CalendarView
from advanced_report_builder.views.datatables.datatables import TableView
from advanced_report_builder.views.error_pod import ErrorPodView
from advanced_report_builder.views.funnel_charts import FunnelChartView
from advanced_report_builder.views.kanban import KanbanView
from advanced_report_builder.views.line_charts import LineChartView
from advanced_report_builder.views.multi_value import MultiValueView
from advanced_report_builder.views.pie_charts import PieChartView
from advanced_report_builder.views.single_values import SingleValueView


class ViewTypes:
    views = {
        'tablereport': TableView,
        'singlevaluereport': SingleValueView,
        'barchartreport': BarChartView,
        'linechartreport': LineChartView,
        'piechartreport': PieChartView,
        'funnelchartreport': FunnelChartView,
        'kanbanreport': KanbanView,
        'calendarreport': CalendarView,
        'multivaluereport': MultiValueView,
        'error': ErrorPodView,
    }

    custom_views = {}
