from django_menus.menu import MenuItem

from advanced_report_builder.views.custom import CustomBaseView


class Custom1(CustomBaseView):
    template_name = 'report_builder_examples/custom1.html'

    def pod_report_menu(self):
        return [('report_builder_examples:index', 'Back', {'css_classes': 'btn-secondary'}),
                MenuItem(f'advanced_report_builder:custom_modal,pk-{self.report.id}',
                         menu_display='Edit',
                         font_awesome='fas fa-pencil-alt')]


class CustomWithQuery(CustomBaseView):
    template_name = 'report_builder_examples/custom_with_queries.html'
    report_type_slug = 'company'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        results = self.get_query_results()
        context['results'] = results
        return context

    def pod_report_menu(self):
        report_type = self.get_report_type()
        return [('report_builder_examples:index', 'Back', {'css_classes': 'btn-secondary'}),
                MenuItem(f'advanced_report_builder:custom_modal,pk-{self.report.id}-report_type-{report_type.id}',
                         menu_display='Edit',
                         font_awesome='fas fa-pencil-alt')]
