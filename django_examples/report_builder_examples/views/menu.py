from ajax_helpers.mixins import AjaxHelpers
from django_menus.menu import MenuMixin


class MainMenu(AjaxHelpers, MenuMixin):

    def setup_menu(self):

        self.add_menu('main_menu').add_items(
            ('report_builder_examples:index', 'Reports'),
            ('report_builder_examples:dashboards_index', 'Dashboard'),
        )