from copy import deepcopy

from django.shortcuts import get_object_or_404

from advanced_report_builder.models import (
    BarChartReport,
    CustomReport,
    FunnelChartReport,
    KanbanReport,
    LineChartReport,
    MultiValueReport,
    PieChartReport,
    SingleValueReport,
    TableReport,
)


class DuplicateReport:
    def duplicate(self, report):
        duplicate_methods = {
            'tablereport': self._duplicate_table_report,
            'singlevaluereport': self._duplicate_single_value_report,
            'barchartreport': self._duplicate_bar_chart_report,
            'linechartreport': self._duplicate_line_chart_report,
            'piechartreport': self._duplicate_pie_chart_report,
            'funnelchartreport': self._duplicate_funnel_chart_report,
            'kanbanreport': self._duplicate_kanban_report,
            'customreport': self._duplicate_custom_report,
            'multivaluereport': self._duplicate_multi_value_report,
        }
        new_report = duplicate_methods[report.instance_type](report_id=report.id)
        return new_report

    def _duplicate_report(self, report, copy_queries=True):
        new_report = deepcopy(report)
        new_report.id = None
        new_report.pk = None
        new_report.slug = None
        new_report.name = f'Copy {new_report.name}'
        new_report.save()
        if copy_queries:
            self._duplicate_queries(report=report, new_report=new_report)
        self._duplicate_report_tags(report=report, new_report=new_report)
        return new_report

    @staticmethod
    def _duplicate_queries(report, new_report):
        report_queries = report.reportquery_set.all()
        for report_query in report_queries:
            new_report_query = deepcopy(report_query)
            new_report_query.id = None
            new_report_query.pk = None
            new_report_query.report = new_report
            new_report_query.save()

    @staticmethod
    def _duplicate_report_tags(report, new_report):
        for report_tag in report.report_tags.all():
            new_report.report_tags.add(report_tag)

    @staticmethod
    def _duplicate_targets(report, new_report):
        for target in report.targets.all():
            new_report.targets.add(target)

    def _duplicate_table_report(self, report_id):
        table_report = get_object_or_404(TableReport, pk=report_id)
        new_table_report = self._duplicate_report(report=table_report)
        return new_table_report

    def _duplicate_single_value_report(self, report_id):
        single_value_report = get_object_or_404(SingleValueReport, pk=report_id)
        new_single_value_report = self._duplicate_report(report=single_value_report)
        return new_single_value_report

    def _duplicate_bar_chart_report(self, report_id):
        bar_chart_report = get_object_or_404(BarChartReport, pk=report_id)
        new_bar_chart_report = self._duplicate_report(report=bar_chart_report)
        return new_bar_chart_report

    def _duplicate_line_chart_report(self, report_id):
        line_chart_report = get_object_or_404(LineChartReport, pk=report_id)
        new_bar_chart_report = self._duplicate_report(report=line_chart_report)
        self._duplicate_targets(report=line_chart_report, new_report=new_bar_chart_report)
        return new_bar_chart_report

    def _duplicate_pie_chart_report(self, report_id):
        pie_report = get_object_or_404(PieChartReport, pk=report_id)
        new_pie_report = self._duplicate_report(report=pie_report)
        return new_pie_report

    def _duplicate_funnel_chart_report(self, report_id):
        funnel_chart_report = get_object_or_404(FunnelChartReport, pk=report_id)
        new_funnel_chart_report = self._duplicate_report(report=funnel_chart_report)
        return new_funnel_chart_report

    def _duplicate_kanban_report(self, report_id):
        kanban_report = get_object_or_404(KanbanReport, pk=report_id)
        new_kanban_report = self._duplicate_report(report=kanban_report, copy_queries=False)
        kanban_report_descriptions = kanban_report.kanbanreportdescription_set.all()
        descriptions_map = {}
        for kanban_report_description in kanban_report_descriptions:
            new_kanban_report_description = deepcopy(kanban_report_description)
            new_kanban_report_description.id = None
            new_kanban_report_description.pk = None
            new_kanban_report_description.kanban_report = new_kanban_report
            new_kanban_report_description.save()
            descriptions_map[kanban_report_description.id] = new_kanban_report_description

        kanban_report_lanes = kanban_report.kanbanreportlane_set.all()
        for kanban_report_lane in kanban_report_lanes:
            new_kanban_report_lane = deepcopy(kanban_report_lane)
            new_kanban_report_lane.id = None
            new_kanban_report_lane.pk = None
            new_kanban_report_lane.kanban_report = new_kanban_report
            kanban_report_description_id = kanban_report_lane.kanban_report_description_id
            new_kanban_report_lane.kanban_report_description = descriptions_map[kanban_report_description_id]
            new_kanban_report_lane.save()
        return new_kanban_report

    def _duplicate_multi_value_report(self, report_id):
        multi_value_report = get_object_or_404(MultiValueReport, pk=report_id)
        new_multi_value_report = self._duplicate_report(report=multi_value_report, copy_queries=False)
        multi_cell_styles = multi_value_report.multicellstyle_set.all()
        multi_cell_styles_map = {}
        for multi_cell_style in multi_cell_styles:
            new_multi_cell_style = deepcopy(multi_cell_style)
            new_multi_cell_style.id = None
            new_multi_cell_style.pk = None
            new_multi_cell_style.multi_value_report = new_multi_value_report
            new_multi_cell_style.save()
            multi_cell_styles_map[multi_cell_style.id] = new_multi_cell_style

        multi_value_held_queries = multi_value_report.multivalueheldquery_set.all()
        multi_value_helds_map = {}
        for multi_value_held_query in multi_value_held_queries:
            new_multi_value_held_query = deepcopy(multi_value_held_query)
            new_multi_value_held_query.id = None
            new_multi_value_held_query.pk = None
            new_multi_value_held_query.multi_value_report = new_multi_value_report
            new_multi_value_held_query.save()
            multi_value_helds_map[multi_value_held_query.id] = new_multi_value_held_query

        multi_value_report_cells = multi_value_report.multivaluereportcell_set.all()
        for multi_value_report_cell in multi_value_report_cells:
            new_multi_value_report_cell = deepcopy(multi_value_report_cell)
            new_multi_value_report_cell.id = None
            new_multi_value_report_cell.pk = None
            new_multi_value_report_cell.multi_value_report = new_multi_value_report
            new_multi_cell_style_id = multi_value_report_cell.multi_cell_style_id
            new_multi_value_report_cell.multi_cell_style = multi_cell_styles_map[new_multi_cell_style_id]
            if multi_value_report_cell.multi_value_held_query is not None:
                multi_value_held_query_id = multi_value_report_cell.multi_value_held_query_id
                new_multi_value_report_cell.multi_value_held_query = multi_value_helds_map[multi_value_held_query_id]

            new_multi_value_report_cell.save()

        multi_value_report_columns = multi_value_report.multivaluereportcolumn_set.all()
        for multi_value_report_column in multi_value_report_columns:
            new_multi_value_report_column = deepcopy(multi_value_report_column)
            new_multi_value_report_column.id = None
            new_multi_value_report_column.pk = None
            new_multi_value_report_column.multi_value_report = new_multi_value_report
            new_multi_value_report_column.save()

        return new_multi_value_report

    def _duplicate_custom_report(self, report_id):
        custom_report = get_object_or_404(CustomReport, pk=report_id)
        new_custom_report = self._duplicate_report(report=custom_report)
        return new_custom_report
