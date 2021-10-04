from django_menus.menu import MenuMixin


class MainMenu(MenuMixin):

    def setup_menu(self):
        super().setup_menu()
        self.add_menu('main_menu').add_items('ajax_main')
