from advanced_report_builder.views.dashboard import ViewDashboardBase
from django.forms import CharField, Textarea
from django_datatables.columns import ColumnLink
from django_datatables.datatables import DatatableView
from django_menus.menu import MenuMixin
from django_modals.fields import FieldEx

from advanced_report_builder.models import Report, Dashboard
from advanced_report_builder.utils import make_slug_str
from advanced_report_builder.views.datatables import TableModal, TableView
from report_builder_examples.views.base import MainMenu, MainIndices


class ViewDashboards(MainIndices):
    model = Dashboard
    table_title = 'Dashboards'

    # def setup_menu(self):
    #     super().setup_menu()
    #     self.add_menu('table_menu', 'button_group').add_items(('advanced_report_builder:table_modal,-',
    #                                                            'Add Table Report'))

    @staticmethod
    def setup_table(table):
        table.add_columns(
            ('id', {'column_defs': {'width': '30px'}}),
            'slug',
            'name',
            # 'instance_type',
            # 'OutputType',
            ColumnLink(column_name='view_dashboard',
                       field='name',
                       link_ref_column='slug',
                       url_name='report_builder_examples:view_dashboard'),
        )


class ViewDashboard(MainMenu, ViewDashboardBase):
    template_name = 'report_builder_examples/dashboard.html'
    # views_overrides = {'tablereport': ViewTableReport}

