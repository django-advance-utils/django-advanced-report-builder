from ajax_helpers.mixins import AjaxHelpers
from django_datatables.datatables import DatatableView
from django_menus.menu import MenuMixin, MenuItem


class MainMenu(AjaxHelpers, MenuMixin):

    def setup_menu(self):

        self.add_menu('main_menu').add_items(
            ('report_builder_examples:index', 'Reports'),
            ('report_builder_examples:dashboards_index', 'Dashboard'),
            MenuItem(url='admin:index',
                     menu_display='Admin',
                     visible=self.request.user.is_superuser),

        )


class MainIndices(MainMenu, DatatableView):
    template_name = 'report_builder_examples/indices.html'
    table_title = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['table_title'] = self.table_title
        return context
