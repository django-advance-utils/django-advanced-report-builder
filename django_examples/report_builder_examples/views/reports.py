from django_datatables.columns import ColumnLink
from django_datatables.datatables import DatatableView
from report_builder_examples.models import Report

from report_builder.views.main import ViewReportBase


class ViewReports(DatatableView):
    model = Report
    template_name = 'report_builder_examples/index.html'

    @staticmethod
    def setup_table(table):
        table.add_columns(
            ('id', {'column_defs': {'width': '30px'}}),
            'name',
            ColumnLink(column_name='view_company', field='name', url_name='report_builder_examples:view_report'),
        )


class ViewReport(ViewReportBase):
    template_name = 'report_builder_examples/report.html'
    model = Report

    def report_menu(self):
        return ['report_builder_examples:index']
