from ajax_helpers.mixins import AjaxHelpers
from django_menus.menu import MenuItem, MenuMixin

from advanced_report_builder.utils import make_slug_str, get_report_builder_class


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

    def queries_option_menus(self, report, dashboard_report):
        query_slug = f'query{report.id}'
        if dashboard_report is not None:
            if not dashboard_report.show_versions:
                return []
            query_slug += f'_{dashboard_report.id}'
        menus = []
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
            menus.append(
                MenuItem(
                    menu_display='Version',
                    no_hover=True,
                    css_classes='btn-secondary',
                    dropdown=dropdown,
                )
            )

        for option in report.reportoption_set.all():
            option_slug = f'option{option.id}'
            base_model = option.content_type.model_class()
            report_cls = get_report_builder_class(model=base_model, class_name=option.report_builder_class_name)
            dropdown = []
            for _obj in base_model.objects.filter(report_cls.options_filter):
                slug_str = make_slug_str(self.slug, overrides={option_slug: _obj.id})
                dropdown.append(
                    (
                        self.request.resolver_match.view_name,
                        _obj.__str__(),
                        {'url_kwargs': {'slug': slug_str}},
                    )
                )
            menus.append(
                MenuItem(
                    menu_display=option.name,
                    no_hover=True,
                    css_classes='btn-secondary',
                    dropdown=dropdown,
                )
            )

        return menus
