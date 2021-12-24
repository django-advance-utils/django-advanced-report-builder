from advanced_report_builder.views.bar_charts import BarChartView
from advanced_report_builder.views.funnel_charts import FunnelChartView
from advanced_report_builder.views.line_charts import LineChartView
from advanced_report_builder.views.pie_charts import PieChartView
from advanced_report_builder.views.single_values import SingleValueView
from django.forms import CharField, Textarea
from django.shortcuts import redirect
from django_datatables.columns import ColumnLink
from django_menus.menu import MenuItem
from django_modals.fields import FieldEx
from report_builder_examples.views.base import MainMenu, MainIndices

from advanced_report_builder.models import Report
from advanced_report_builder.utils import make_slug_str
from advanced_report_builder.views.datatables import TableModal, TableView
from advanced_report_builder.views.reports import ViewReportBase


class ViewReports(MainIndices):
    model = Report
    table_title = 'Reports'

    def setup_menu(self):
        super().setup_menu()
        self.add_menu('table_menu', 'button_group').add_items(
            MenuItem(menu_display='Add', no_hover=True, css_classes='btn-secondary',
                     dropdown=[MenuItem('advanced_report_builder:table_modal,-', 'Add Table Report'),
                               MenuItem('advanced_report_builder:single_value_modal,-',
                                        'Add Single Value Report'),
                               MenuItem('advanced_report_builder:bar_chart_modal,-',
                                        'Add Bar Chart Report'),
                               MenuItem('advanced_report_builder:line_chart_modal,-',
                                        'Add Line Chart Report'),
                               MenuItem('advanced_report_builder:pie_chart_modal,-',
                                        'Add Pie Chart Report'),
                               MenuItem('advanced_report_builder:funnel_chart_modal,-',
                                        'Add Funnel Chart Report')]),
        )

    @staticmethod
    def setup_table(table):
        table.add_columns(
            ('id', {'column_defs': {'width': '30px'}}),
            'slug',
            'name',
            'instance_type',
            'OutputType',
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
        return [('report_builder_examples:index', 'Back', {'css_classes': 'btn-secondary'}),
                *super().pod_report_menu()]

    def queries_menu(self):
        report_queries = self.table_report.reportquery_set.all()
        if len(report_queries) > 1:
            dropdown = []
            for report_query in report_queries:
                slug_str = make_slug_str(self.slug, overrides={f'query{self.table_report.id}': report_query.id})
                dropdown.append(('report_builder_examples:view_report',
                                 report_query.name, {'url_kwargs': {'slug': slug_str}}))
            # name = self.get_report_query().name

            # return [MenuItem(menu_display=name, no_hover=True, css_classes='btn-secondary',
            #                  dropdown=dropdown)]
            return dropdown
        return []


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


class ViewReport(MainMenu, ViewReportBase):
    template_name = 'report_builder_examples/report.html'
    views_overrides = {'tablereport': ViewTableReport,
                       'singlevaluereport': ViewSingleValueReport,
                       'barchartreport': ViewBarChartReport,
                       'linechartreport': ViewLineChartReport,
                       'piechartreport': ViewPieChartReport,
                       'funnelchartreport': ViewFunnelChartReport,
                       }

    def redirect_url(self):
        return redirect('report_builder_examples:view_report', slug=self.report.slug)


class TableExtraModal(TableModal):

    def form_setup(self, form, *_args, **_kwargs):
        form.fields['notes'] = CharField(widget=Textarea)

        return [FieldEx('name'),
                FieldEx('notes'),
                FieldEx('has_clickable_rows', template='django_modals/fields/label_checkbox.html')]
