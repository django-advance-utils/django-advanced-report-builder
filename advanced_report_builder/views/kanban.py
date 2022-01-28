import json

from ajax_helpers.mixins import AjaxHelpers
from django.apps import apps
from django.forms import CharField
from django.http import JsonResponse
from django.views.generic import TemplateView
from django_datatables.widgets import DataTableReorderWidget
from django_menus.menu import MenuItem, MenuMixin
from django_modals.datatables import EditColumn
from django_modals.fields import FieldEx
from django_modals.modals import ModelFormModal
from django_modals.processes import PROCESS_EDIT_DELETE, PERMISSION_OFF
from django_modals.widgets.select2 import Select2Multiple, Select2

from advanced_report_builder.columns import ReportBuilderNumberColumn
from advanced_report_builder.data_merge.widget import DataMergeWidget
from advanced_report_builder.filter_query import FilterQueryMixin
from advanced_report_builder.models import KanbanReport, KanbanReportLane
from advanced_report_builder.utils import crispy_modal_link_args, get_django_field
from advanced_report_builder.views.modals_base import QueryBuilderModalBase


class KanbanView(AjaxHelpers, FilterQueryMixin, MenuMixin, TemplateView):
    number_field = ReportBuilderNumberColumn
    template_name = 'advanced_report_builder/kanban/report.html'

    def __init__(self, *args, **kwargs):
        self.chart_report = None
        super().__init__(*args, **kwargs)

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
            *self.queries_menu(),
        )

    def dispatch(self, request, *args, **kwargs):
        self.report = kwargs.get('report')
        self.chart_report = self.report.kanbanreport
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['title'] = self.get_title()
        # self.table.single_value = self.chart_report
        # self.table.datatable_template = 'advanced_report_builder/single_values/middle.html'
        context['kanban_report'] = self.chart_report
        return context

    def pod_dashboard_view_menu(self):
        return []

    def pod_report_menu(self):
        return [MenuItem(f'advanced_report_builder:kanban_modal,pk-{self.chart_report.id}',
                         menu_display='Edit',
                         font_awesome='fas fa-pencil-alt', css_classes=['btn-primary'])]

    def pod_dashboard_edit_menu(self):
        return [MenuItem(f'advanced_report_builder:dashboard_report_modal,pk-{self.dashboard_report.id}',
                         menu_display='Edit',
                         font_awesome='fas fa-pencil-alt', css_classes=['btn-primary'])]

    def queries_menu(self):
        return []


class KanbanModal(ModelFormModal):
    size = 'xl'
    process = PROCESS_EDIT_DELETE
    permission_delete = PERMISSION_OFF
    model = KanbanReport
    widgets = {'report_tags': Select2Multiple}
    ajax_commands = ['datatable', 'button']

    form_fields = ['name',
                   'report_tags']

    def form_setup(self, form, *_args, **_kwargs):
        org_id = self.object.id if hasattr(self, 'object') else None

        if org_id is not None:
            form.fields['order'] = CharField(
                required=False,
                widget=DataTableReorderWidget(
                    model=KanbanReportLane,
                    order_field='order',
                    fields=['_.index',
                            '.id',
                            'name',
                            EditColumn('advanced_report_builder:kanban_lane_modal')],
                    attrs={'filter': {'kanban_report__id': self.object.id}})
            )

            return [*self.form_fields,
                    crispy_modal_link_args('advanced_report_builder:kanban_lane_modal', 'Add Lane',
                                           'kanban_report_id-', self.object.id, div=True,
                                           div_classes='float-right', button_classes='btn btn-primary',
                                           font_awesome='fa fa-plus'),
                    'order']

    def datatable_sort(self, **kwargs):
        current_sort = dict(KanbanReportLane.objects.filter(kanban_report=self.object.id).values_list('id', 'order'))
        for s in kwargs['sort']:
            if current_sort[s[1]] != s[0]:
                o = KanbanReportLane.objects.get(id=s[1])
                o.order = s[0]
                o.save()
        return self.command_response('')

    def post_save(self, created):
        if created:
            self.modal_redirect(self.request.resolver_match.view_name, slug=f'pk-{self.object.id}')


class KanbanLaneModal(QueryBuilderModalBase):
    template_name = 'advanced_report_builder/kanban/modal.html'
    size = 'xl'
    process = PROCESS_EDIT_DELETE
    permission_delete = PERMISSION_OFF
    model = KanbanReportLane

    widgets = {'report_tags': Select2Multiple}

    form_fields = ['name',
                   'report_type',
                   'heading_field',
                   'description',
                   'query_data']

    def form_setup(self, form, *_args, **_kwargs):
        fields = []
        if form.instance.heading_field:

            form.fields['heading_field'].initial = form.instance.heading_field

            # base_model = form.instance.report_type.content_type.model_class()
            # report_builder_fields = getattr(base_model, form.instance.report_type.report_builder_class_name, None)
            # tables = []
            # self._get_fields(base_model=base_model,
            #                  fields=fields,
            #                  tables=tables,
            #                  report_builder_fields=report_builder_fields,
            #                  selected_field_id=form.instance.heading_field,
            #                  for_select2=True)

        form.fields['heading_field'].widget = Select2(attrs={'ajax': True})
        form.fields['heading_field'].widget.select_data = fields

        form.fields['description'].widget = DataMergeWidget()

        return ('name',
                'report_type',
                'heading_field',
                'description',
                FieldEx('query_data',
                        template='advanced_report_builder/query_builder.html'),
                )

    def select2_heading_field(self, **kwargs):
        fields = []
        if kwargs['report_type'] != '':
            report_builder_fields, base_model = self.get_report_builder_fields(report_type_id=kwargs['report_type'])
            fields = []
            tables = []
            self._get_fields(base_model=base_model,
                             fields=fields,
                             tables=tables,
                             report_builder_fields=report_builder_fields,
                             for_select2=True,
                             all_fields=True)

        return JsonResponse({'results': fields})

    def _get_menu_fields(self, base_model, menus, report_builder_fields, code_prefix='', previous_base_model=None):

        for report_builder_field in report_builder_fields.fields:
            django_field, col_type_override, columns = get_django_field(base_model=base_model,
                                                                        field=report_builder_field)
            for column in columns:
                full_id = code_prefix + column.column_name
                menus.append({'code': full_id, 'text': column.title})

        for include in report_builder_fields.includes:
            app_label, model, report_builder_fields_str = include['model'].split('.')

            new_model = apps.get_model(app_label, model)
            if new_model != previous_base_model:
                new_report_builder_fields = getattr(new_model, report_builder_fields_str, None)
                title = new_report_builder_fields.title
                menu = []
                self._get_menu_fields(base_model=new_model,
                                      menus=menu,
                                      report_builder_fields=new_report_builder_fields,
                                      code_prefix=f"{code_prefix}{include['field']}__",
                                      previous_base_model=base_model)
                menus.append({'text': title, 'menu': menu})

    def ajax_get_data_merge_menu(self, **kwargs):
        field_auto_id = kwargs['field_auto_id']
        menus = []
        if kwargs['report_type'] != '':
            report_builder_fields, base_model = self.get_report_builder_fields(report_type_id=kwargs['report_type'])

            self._get_menu_fields(base_model=base_model,
                                  menus=menus,
                                  report_builder_fields=report_builder_fields)

            menus = [{'code': 'data_merge',
                      'text': 'Data Merge',
                      'menu': menus}]

        return self.command_response(f'build_data_merge_menu_{field_auto_id}',
                                     data=json.dumps(menus))
