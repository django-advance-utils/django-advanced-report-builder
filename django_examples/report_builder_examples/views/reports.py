from crispy_forms.layout import Field
from django.forms import CharField, Textarea
from django_datatables.columns import ColumnLink
from django_datatables.datatables import DatatableView
from django_modals.fields import FieldEx

from report_builder.models import Report
from report_builder.views.datatables import TableModal
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

# class ViewTable(ViewReportBase):


class ViewReport(ViewReportBase):
    template_name = 'report_builder_examples/report.html'


class TableExtraModal(TableModal):



    def form_setup(self, form, *_args, **_kwargs):
        form.fields['notes'] = CharField(widget=Textarea)



        return [FieldEx('name'),
                FieldEx('notes'),
                FieldEx('has_clickable_rows', template='django_modals/fields/label_checkbox.html')]







