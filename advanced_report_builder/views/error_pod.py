from django_menus.menu import MenuItem

from advanced_report_builder.views.custom import CustomBaseView


class ErrorPodView(CustomBaseView):
    template_name = 'advanced_report_builder/error.html'
    report_type_slug = 'company'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.enable_queries = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['error_message'] = self.extra_kwargs.get('error_message')
        return context

    def pod_report_menu(self):
        report_type = self.get_report_type()
        return [
            ('report_builder_examples:index', 'Back', {'css_classes': 'btn-secondary'}),
            MenuItem(
                f'advanced_report_builder:custom_modal,pk-{self.report.id}-report_type-{report_type.id}',
                menu_display='Edit',
                font_awesome='fas fa-pencil-alt',
            ),
        ]

    def setup_menu(self):
        super().setup_menu()
        if not self.show_toolbar:
            return

        if self.dashboard_report and self.enable_edit:
            report_menu = self.pod_dashboard_edit_menu()
        elif self.dashboard_report and not self.enable_edit:
            report_menu = self.pod_dashboard_view_menu()
        else:
            view = self.extra_kwargs.get('report_cls')(*self.args, **self.kwargs)
            report_menu = view.edit_report_menu(request=self.request, chart_report_id=self.report.id, slug_str='')
        if self.enable_queries:
            self.add_menu('button_menu', 'button_group').add_items(
                *report_menu,
                *self.queries_option_menus(report=self.report, dashboard_report=self.dashboard_report),
            )
        else:
            self.add_menu('button_menu', 'button_group').add_items(
                *report_menu,
            )
