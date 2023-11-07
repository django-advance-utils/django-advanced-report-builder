from django_menus.menu import MenuItem

from advanced_report_builder.models import ReportType
from advanced_report_builder.views.custom import CustomBaseView
from report_builder_examples.models import Company


class Custom1(CustomBaseView):
    template_name = 'report_builder_examples/custom1.html'

    def pod_report_menu(self):
        return [('report_builder_examples:index', 'Back', {'css_classes': 'btn-secondary'}),
                MenuItem(f'advanced_report_builder:custom_modal,pk-{self.report.id}',
                                      menu_display='Edit',
                                      font_awesome='fas fa-pencil-alt')]

class CustomWithQuery(CustomBaseView):
    template_name = 'report_builder_examples/custom_with_queries.html'

    def get_report_type(self):
        return ReportType.objects.get(slug='company')

    def get_default_query(self):
        return Company.objects.all()

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
