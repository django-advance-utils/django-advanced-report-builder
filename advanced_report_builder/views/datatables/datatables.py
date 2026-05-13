from django.core.exceptions import FieldDoesNotExist, FieldError
from django.db import ProgrammingError
from django_datatables.datatables import DatatableError, DatatableView
from django_datatables.helpers import row_link
from django_menus.menu import MenuItem

from advanced_report_builder.columns import ArrowColumn
from advanced_report_builder.exceptions import ReportError
from advanced_report_builder.record_nav import RecordNavPlugin
from advanced_report_builder.utils import get_report_builder_class, split_slug
from advanced_report_builder.views.datatables.utils import TableUtilsMixin
from advanced_report_builder.views.report import ReportBase


class TableView(ReportBase, TableUtilsMixin, DatatableView):
    template_name = 'advanced_report_builder/datatables/report.html'
    menu_display = ''

    def __init__(self, *args, **kwargs):
        self.table_id = None
        super().__init__(*args, **kwargs)

    def add_tables(self):
        return None

    def dispatch(self, request, *args, **kwargs):
        self.slug = split_slug(self.kwargs['slug'])
        self.report = kwargs.get('report')
        self.table_report = self.report.tablereport
        self.dashboard_report = kwargs.get('dashboard_report')
        self.enable_edit = kwargs.get('enable_edit')
        if self.dashboard_report:
            self.table_id = f'tabledashboard_{self.dashboard_report.id}'
        else:
            self.table_id = f'table_{self.table_report.id}'

        self.base_model = self.table_report.get_base_model()
        self.add_table(self.table_id, model=self.base_model)

        try:
            return super().dispatch(request, *args, **kwargs)
        except DatatableError as de:
            raise ReportError(de.args[0])
        except ProgrammingError as de:
            raise ReportError(de.args[0])

    def setup_table(self, table):
        table.extra_filters = self.extra_filters
        base_model = self.table_report.get_base_model()
        table_fields = self.table_report.table_fields
        pivot_fields = self.table_report.pivot_fields
        fields_used = set()
        fields_map = {}
        report_builder_class = get_report_builder_class(model=base_model, report_type=self.table_report.report_type)
        try:
            self.process_query_results(
                report_builder_class=report_builder_class,
                table=table,
                base_model=base_model,
                fields_used=fields_used,
                fields_map=fields_map,
                table_fields=table_fields,
                pivot_fields=pivot_fields,
            )
        except (FieldError, FieldDoesNotExist) as e:
            raise ReportError(e)
        if self.table_report.order_by_field:
            order_by_field = self.table_report.order_by_field
            if order_by_field not in fields_used:
                table.add_columns(f'.{order_by_field}')
            elif order_by_field in fields_map:
                order_by_field = fields_map[order_by_field]
            if self.table_report.order_by_ascending:
                table.sort(order_by_field)
            else:
                table.sort(f'-{order_by_field}')

        table.table_options['pageLength'] = self.table_report.page_length
        table.table_options['bStateSave'] = False

        if self.table_report.has_clickable_rows and self.table_report.link_field and self.kwargs.get('enable_links'):
            table.table_classes.append('row_link')
            table.add_columns(ArrowColumn(column_name='arrow_icon'))
            _, col_type_override, _, _ = self.get_field_details(
                base_model=base_model,
                field=self.table_report.link_field,
                report_builder_class=report_builder_class,
            )
            field = col_type_override.field[0] if isinstance(col_type_override.field, list) else 'id'
            if field not in fields_used:
                table.add_columns(f'.{field}')
            table.table_options['row_href'] = row_link(col_type_override.url, field)

        if self.table_report.record_nav:
            table.add_plugin(RecordNavPlugin, self.get_title())

    def add_to_context(self, **kwargs):
        return {'title': self.get_title(), 'table_report': self.table_report}

    def setup_menu(self):
        super().setup_menu()
        if self.dashboard_report and self.enable_edit:
            report_menu = self.pod_dashboard_edit_menu()
        elif self.dashboard_report and not self.enable_edit:
            report_menu = self.pod_dashboard_view_menu()
        else:
            report_menu = self.pod_report_menu()

        self.add_menu('button_menu', 'button_group').add_items(
            *report_menu,
            *self.queries_option_menus(report=self.report, dashboard_report=self.dashboard_report),
        )

    def pod_dashboard_edit_menu(self):
        return [
            MenuItem(
                f'advanced_report_builder:dashboard_report_modal,pk-{self.dashboard_report.id}',
                menu_display='Edit',
                font_awesome='fas fa-pencil-alt',
                css_classes=['btn-primary'],
            )
        ]

    # noinspection PyMethodMayBeStatic
    def pod_dashboard_view_menu(self):
        return []

    def pod_report_menu(self):
        query_id = self.slug.get(f'query{self.table_report.id}')
        slug_str = ''
        if query_id:
            slug_str = f'-query_id-{query_id}'

        return [
            *self.version_management_menu(),
            *self.edit_report_menu(
                request=self.request,
                chart_report_id=self.table_report.id,
                slug_str=slug_str,
            ),
        ]

    def edit_report_menu(self, request, chart_report_id, slug_str):
        return [
            MenuItem(
                f'advanced_report_builder:table_modal,pk-{chart_report_id}{slug_str}',
                menu_display='Edit',
                font_awesome='fas fa-pencil-alt',
                css_classes=['btn-primary'],
            ),
            *self.duplicate_menu(request=self.request, report_id=chart_report_id),
        ]

    # Where the New/Edit Version items live in the UI:
    # - True  (default)  : inside the Version dropdown, after a divider.
    # - False             : as top-level toolbar buttons.
    # Consumers can flip this per-subclass to suit their toolbar layout.
    version_management_in_dropdown = True

    def can_manage_versions(self):
        """Permission hook: return True if the current user is allowed to
        add/edit/delete ReportQuery versions through the report toolbar.

        Consumers (e.g. JMS Cloud) should override this to plug in their
        own user/role/tenant permission logic. The library default is
        permissive: the per-report ``allow_new_version`` flag is treated
        as the opt-in, with no additional user check.
        """
        return True

    def force_show_version_menu(self, report):
        # Keep the Version dropdown visible whenever the per-report
        # opt-in is on, even when only 0 or 1 saved queries exist, so
        # users always have a clear place to add a new version.
        return self.table_report.allow_new_version

    def _version_management_targets(self):
        """Return ``(new_query_slug, edit_query_slug_or_None)`` if version
        management should be exposed for this report, otherwise ``None``.
        """
        if not self.table_report.allow_new_version:
            return None
        if not self.can_manage_versions():
            return None

        report_type_id = self.table_report.report_type_id
        new_slug = f'report_id-{self.table_report.id}-report_type-{report_type_id}-show_order_by-1-show_target-0'

        # Edit targets the currently-selected version (or the first one
        # if nothing explicitly selected). Goes to the same QueryModal
        # in edit-with-delete mode.
        current_query_id = self.slug.get(f'query{self.table_report.id}')
        if current_query_id is None:
            first_query = self.table_report.reportquery_set.order_by('order').first()
            current_query_id = first_query.id if first_query else None

        edit_slug = None
        if current_query_id is not None:
            edit_slug = f'pk-{current_query_id}-report_type-{report_type_id}-show_order_by-1-show_target-0'
        return new_slug, edit_slug

    def version_management_menu(self):
        """Top-level toolbar items for adding / editing saved query
        versions. Empty when items live inside the Version dropdown."""
        if self.version_management_in_dropdown:
            return []
        targets = self._version_management_targets()
        if targets is None:
            return []
        new_slug, edit_slug = targets
        items = [
            MenuItem(
                f'advanced_report_builder:query_modal,{new_slug}',
                menu_display='New Version',
                font_awesome='fas fa-save',
                css_classes='btn btn-outline-primary',
            ),
        ]
        if edit_slug is not None:
            items.append(
                MenuItem(
                    f'advanced_report_builder:query_modal,{edit_slug}',
                    menu_display='Edit Version',
                    font_awesome='fas fa-pencil-alt',
                    css_classes='btn btn-outline-secondary',
                )
            )
        return items

    def version_dropdown_extras(self, report):
        """Items appended to the Version dropdown (after a divider) when
        items live in the dropdown (the library default)."""
        if not self.version_management_in_dropdown:
            return []
        targets = self._version_management_targets()
        if targets is None:
            return []
        new_slug, edit_slug = targets
        items = [
            MenuItem(
                f'advanced_report_builder:query_modal,{new_slug}',
                menu_display='Create New Version',
                font_awesome='fas fa-save',
            ),
        ]
        if edit_slug is not None:
            items.append(
                MenuItem(
                    f'advanced_report_builder:query_modal,{edit_slug}',
                    menu_display='Edit Current Version',
                    font_awesome='fas fa-pencil-alt',
                )
            )
        return items

    def get_dashboard_class(self, report):
        pivot_fields = report.tablereport.pivot_fields
        if pivot_fields is not None and len(pivot_fields) > 0:
            return 'p-0'
        return ''
