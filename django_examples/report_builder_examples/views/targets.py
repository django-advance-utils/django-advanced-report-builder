from django_datatables.columns import ColumnLink
from django_modals.datatables import EditColumn
from report_builder_examples.views.base import MainMenu, MainIndices

from advanced_report_builder.models import Target


class ViewTargets(MainIndices):
    model = Target
    table_title = 'colour'

    def setup_menu(self):
        super().setup_menu()
        self.add_menu('table_menu', 'button_group').add_items(('advanced_report_builder:target_modal,-',
                                                               'Add Target'))

    @staticmethod
    def setup_table(table):
        table.add_columns(
            ('id', {'column_defs': {'width': '30px'}}),
            'slug',
            'name',

            # 'instance_type',
            # 'OutputType',
            EditColumn('advanced_report_builder:target_modal'),
        )
