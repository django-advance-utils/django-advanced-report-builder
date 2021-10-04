
from report_builder_examples.models import Report

from report_builder.views.main import ViewReportBase


class ViewReport(ViewReportBase):
    template_name = 'report_builder_examples/report.html'
    model = Report
