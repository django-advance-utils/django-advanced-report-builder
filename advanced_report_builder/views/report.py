from ajax_helpers.mixins import AjaxHelpers
from django_menus.menu import MenuItem, MenuMixin


class ReportBase(AjaxHelpers, MenuMixin):
    # noinspection PyUnusedLocal
    @staticmethod
    def duplicate_menu(request, report_id):
        return [MenuItem(f'advanced_report_builder:duplicate_report_modal,pk-{report_id}',
                         css_classes=['btn-success'])]

    def get_dashboard_class(self, report):
        return None
