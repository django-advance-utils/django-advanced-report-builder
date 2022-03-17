from django.views.generic import TemplateView
from django_menus.menu import MenuMixin, MenuItem
from django_modals.modals import ModelFormModal
from django_modals.processes import PROCESS_EDIT_DELETE, PERMISSION_OFF
from django_modals.widgets.select2 import Select2Multiple

from advanced_report_builder.models import CustomReport
from advanced_report_builder.utils import split_slug


class CustomBaseView(MenuMixin, TemplateView):

    def __init__(self, **kwargs):
        self.report = None
        self.slug = None
        self.enable_edit = None
        self.dashboard_report = None
        self.show_toolbar = False
        super().__init__(**kwargs)

    def dispatch(self, request, *args, **kwargs):
        self.report = kwargs.get('report')
        self.slug = split_slug(kwargs.get('slug'))
        self.enable_edit = kwargs.get('enable_edit')
        self.dashboard_report = kwargs.get('dashboard_report')
        if self.enable_edit or (self.dashboard_report and not self.dashboard_report.top) or not self.dashboard_report:
            self.show_toolbar = True
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['report'] = self.report
        context['show_toolbar'] = self.show_toolbar
        context['title'] = self.get_title()
        return context

    def setup_menu(self):
        super().setup_menu()
        if not self.show_toolbar:
            return

        if self.dashboard_report and self.enable_edit:
            report_menu = self.pod_dashboard_edit_menu()
        elif self.dashboard_report and not self.enable_edit:
            report_menu = self.pod_dashboard_view_menu()
        else:
            report_menu = self.pod_report_menu()

        self.add_menu('button_menu', 'button_group').add_items(
            *report_menu,
            *self.queries_menu()
        )

    def pod_dashboard_edit_menu(self):
        return [MenuItem(f'advanced_report_builder:dashboard_report_modal,pk-{self.dashboard_report.id}',
                         menu_display='Edit',
                         font_awesome='fas fa-pencil-alt', css_classes=['btn-primary'])]

    # noinspection PyMethodMayBeStatic
    def pod_dashboard_view_menu(self):
        return []

    # noinspection PyMethodMayBeStatic
    def pod_report_menu(self):
        return []

    def get_title(self):
        if self.dashboard_report and self.dashboard_report.name_override:
            return self.dashboard_report.name_override
        else:
            return self.report.name

    # noinspection PyMethodMayBeStatic
    def queries_menu(self):
        return []

    def get_dashboard_class(self, report):
        return None


class CustomModal(ModelFormModal):
    process = PROCESS_EDIT_DELETE
    permission_delete = PERMISSION_OFF
    model = CustomReport

    widgets = {'report_tags': Select2Multiple}

    form_fields = ['name',
                   'report_tags',
                   'notes']
