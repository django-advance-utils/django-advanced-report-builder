from django.shortcuts import redirect
from django_datatables.columns import ColumnLink
from django_menus.menu import MenuItem
from report_builder_examples.views.base import MainMenu, MainIndices

from advanced_report_builder.models import Dashboard
from advanced_report_builder.views.dashboard import ViewDashboardBase
from report_builder_examples.views.custom import Custom1


class ViewDashboards(MainIndices):
    model = Dashboard
    table_title = 'Dashboards'


    def setup_menu(self):
        super().setup_menu()
        self.add_menu('table_menu', 'button_group').add_items(('advanced_report_builder:dashboard_modal,-',
                                                               'Add Dashboard'))

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
    enable_edit = False
    template_name = 'report_builder_examples/dashboard.html'
    # views_overrides = {'tablereport': ViewTableReport}
    custom_views = {'custom1': Custom1}

    def setup_menu(self):
        super().setup_menu()

        if not self.enable_edit:
            report_menu = [MenuItem('report_builder_examples:edit_dashboard', 'Enable Edit',
                                    url_kwargs={'slug': self.kwargs['slug']})]
        else:
            report_menu = [MenuItem('report_builder_examples:view_dashboard', 'View Only',
                                    url_kwargs={'slug': self.kwargs['slug']}, css_classes='btn-success'),
                           MenuItem('advanced_report_builder:dashboard_modal', 'Edit',
                                    url_kwargs={'slug': self.dashboard.id}),
                           MenuItem('advanced_report_builder:add_dashboard_report', 'Add Report',
                                    url_kwargs={'slug': self.dashboard.id}, css_classes='btn-secondary'),

                           ]

        if report_menu:
            self.add_menu('dashboard_buttons', 'button_group').add_items(
                *report_menu,
            )

    def redirect_url(self):
        if self.enable_edit:
            return redirect('report_builder_examples:edit_dashboard', slug=self.dashboard.slug)
        else:
            return redirect('report_builder_examples:view_dashboard', slug=self.dashboard.slug)
