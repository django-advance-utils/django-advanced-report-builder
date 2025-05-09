from django.views.generic import TemplateView
from django_menus.menu import MenuItem
from django_modals.modals import ModelFormModal
from django_modals.processes import PERMISSION_OFF, PROCESS_EDIT_DELETE
from django_modals.widgets.select2 import Select2Multiple

from advanced_report_builder.filter_query import FilterQueryMixin
from advanced_report_builder.models import CustomReport, ReportType
from advanced_report_builder.utils import split_slug
from advanced_report_builder.views.query_modal.mixin import MultiQueryModalMixin
from advanced_report_builder.views.report import ReportBase


class CustomBaseView(ReportBase, FilterQueryMixin, TemplateView):
    report_type_slug = None

    def __init__(self, **kwargs):
        self.report = None
        self.slug = None
        self.enable_edit = None
        self.dashboard_report = None
        self.show_toolbar = False
        self.enable_queries = True
        self._report_type = None
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
            *self.queries_menu(report=self.report, dashboard_report=self.dashboard_report),
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

    # noinspection PyMethodMayBeStatic
    def pod_report_menu(self):
        return []

    def get_title(self):
        if self.dashboard_report and self.dashboard_report.name_override:
            return self.dashboard_report.name_override
        else:
            return self.report.name

    def get_report_type(self):
        if self.report_type_slug is not None:
            if self._report_type is None:
                self._report_type = ReportType.objects.get(slug=self.report_type_slug)
            return self._report_type
        return None

    def get_default_query(self):
        report_type = self.get_report_type()
        if report_type is not None:
            base_model = report_type.content_type.model_class()
            return base_model.objects.all()
        return None

    def get_default_filter(self, query):
        return query

    def get_query_results(self):
        query = self.get_default_query()
        if query is None:
            return None
        report_query = self.get_report_query(report=self.report)
        if report_query:
            query = self.process_query_filters(query=query, search_filter_data=report_query.query)
            report_type = self.get_report_type()
            if report_type is not None:
                base_model = report_type.content_type.model_class()
                query = self.apply_order_by(
                    query=query,
                    report_query=report_query,
                    report_type=report_type,
                    base_model=base_model,
                )
            return query
        return self.get_default_filter(query)


class CustomModal(MultiQueryModalMixin, ModelFormModal):
    process = PROCESS_EDIT_DELETE
    permission_delete = PERMISSION_OFF
    model = CustomReport
    ajax_commands = ['datatable', 'button']

    widgets = {'report_tags': Select2Multiple}

    form_fields = ['name', 'report_tags', 'notes']

    def form_setup(self, form, *_args, **_kwargs):
        fields = [*self.form_fields]
        if self.object.id and 'report_type' in self.slug:
            self.add_extra_queries(form=form, fields=fields)
        return fields

    def get_report_type(self, **_kwargs):
        return self.slug['report_type']
