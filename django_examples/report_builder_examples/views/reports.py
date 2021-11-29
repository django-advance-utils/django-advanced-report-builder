from django.forms import CharField, Textarea
from django_datatables.columns import ColumnLink
from django_datatables.datatables import DatatableView
from django_menus.menu import MenuMixin
from django_modals.fields import FieldEx

from advanced_report_builder.models import Report
from advanced_report_builder.utils import make_slug_str
from advanced_report_builder.views.datatables import TableModal, TableView
from advanced_report_builder.views.main import ViewReportBase


class ViewReports(MenuMixin, DatatableView):
    model = Report
    template_name = 'report_builder_examples/index.html'

    def setup_menu(self):
        super().setup_menu()
        self.add_menu('table_menu', 'button_group').add_items(('advanced_report_builder:table_modal,-',
                                                               'Add Table Report'))

    @staticmethod
    def setup_table(table):
        table.add_columns(
            ('id', {'column_defs': {'width': '30px'}}),
            'name',
            ColumnLink(column_name='view_company', field='name', url_name='report_builder_examples:view_report'),
        )


class ViewTableReport(TableView):
    def pod_menu(self):
        return [('report_builder_examples:index', 'Back', {'css_classes': 'btn-secondary'}),
                *super().pod_menu()]

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


class ViewReport(ViewReportBase):
    template_name = 'report_builder_examples/report.html'
    views = {'tablereport': ViewTableReport}


class TableExtraModal(TableModal):

    def form_setup(self, form, *_args, **_kwargs):
        form.fields['notes'] = CharField(widget=Textarea)

        return [FieldEx('name'),
                FieldEx('notes'),
                FieldEx('has_clickable_rows', template='django_modals/fields/label_checkbox.html')]







