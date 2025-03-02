from ajax_helpers.mixins import AjaxHelpers
from django_menus.menu import MenuItem, MenuMixin

from advanced_report_builder.utils import make_slug_str


class ReportBase(AjaxHelpers, MenuMixin):
    # noinspection PyUnusedLocal
    @staticmethod
    def duplicate_menu(request, report_id):
        return [
            MenuItem(
                f'advanced_report_builder:duplicate_report_modal,pk-{report_id}',
                css_classes=['btn-success'],
            )
        ]

    def get_dashboard_class(self, report):
        return None

    def queries_menu(self, report, dashboard_report):
        query_slug = f'query{report.id}'
        if dashboard_report is not None:
            if not dashboard_report.show_versions:
                return []
            query_slug += f'_{dashboard_report.id}'

        report_queries = report.reportquery_set.all()
        if len(report_queries) > 1:
            dropdown = []
            for report_query in report_queries:
                slug_str = make_slug_str(self.slug, overrides={query_slug: report_query.id})
                dropdown.append(
                    (
                        self.request.resolver_match.view_name,
                        report_query.name,
                        {'url_kwargs': {'slug': slug_str}},
                    )
                )
            return [
                MenuItem(
                    menu_display='Version',
                    no_hover=True,
                    css_classes='btn-secondary',
                    dropdown=dropdown,
                )
            ]
        return []
