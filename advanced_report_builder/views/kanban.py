import json

from django.conf import settings
from django.forms import CharField
from django.http import JsonResponse
from django.template import Template, Context, TemplateSyntaxError
from django.urls import reverse
from django.views.generic import TemplateView
from django_datatables.columns import ColumnBase
from django_datatables.widgets import DataTableReorderWidget
from django_menus.menu import MenuItem
from django_modals.datatables import EditColumn
from django_modals.fields import FieldEx
from django_modals.modals import ModelFormModal
from django_modals.processes import PROCESS_EDIT_DELETE, PERMISSION_OFF
from django_modals.widgets.select2 import Select2Multiple, Select2

from advanced_report_builder.columns import ReportBuilderNumberColumn
from advanced_report_builder.data_merge.utils import get_menu_fields, get_data_merge_columns
from advanced_report_builder.data_merge.widget import DataMergeWidget
from advanced_report_builder.filter_query import FilterQueryMixin
from advanced_report_builder.models import KanbanReport, KanbanReportLane
from advanced_report_builder.toggle import RBToggle
from advanced_report_builder.utils import crispy_modal_link_args
from advanced_report_builder.views.charts_base import ChartJSTable
from advanced_report_builder.views.modals_base import QueryBuilderModalBase
from advanced_report_builder.views.report import ReportBase


class DescriptionColumn(ColumnBase):
    def row_result(self, data, _page_data):
        html = self.options['html']
        try:
            template = Template(html)
            context = Context(data)
            return template.render(context)
        except TemplateSyntaxError:
            return 'Error in description'


class KanbanView(ReportBase, FilterQueryMixin, TemplateView):
    number_field = ReportBuilderNumberColumn
    template_name = 'advanced_report_builder/kanban/report.html'
    chart_js_table = ChartJSTable

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
        kanban_report_lanes = self.chart_report.kanbanreportlane_set.all()
        lanes = []
        for kanban_report_lane in kanban_report_lanes:
            base_model = kanban_report_lane.get_base_modal()
            table = self.chart_js_table(model=base_model)

            report_builder_class = getattr(base_model, kanban_report_lane.report_type.report_builder_class_name, None)

            columns = get_data_merge_columns(base_model=base_model,
                                             report_builder_class=report_builder_class,
                                             html=kanban_report_lane.description)
            if kanban_report_lane.heading_field is not None:
                table.add_columns(kanban_report_lane.heading_field)

            if kanban_report_lane.description is not None:
                table.add_columns(DescriptionColumn(column_name='test', field='', html=kanban_report_lane.description))
            table.add_columns(*columns)
            table.datatable_template = 'advanced_report_builder/kanban/middle.html'

            if kanban_report_lane.order_by_field:
                if kanban_report_lane.order_by_ascending:
                    table.order_by = [kanban_report_lane.order_by_field]
                else:
                    table.order_by = [f'-{kanban_report_lane.order_by_field}']

            table.query_data = kanban_report_lane.query_data
            table.view_filter = self.view_filter
            lanes.append({'datatable': table,
                          'kanban_report_lane': kanban_report_lane})

        context['kanban_report'] = self.chart_report
        context['lanes'] = lanes
        return context

    def view_filter(self, query, table):
        if not table.query_data:
            return query

        return self.process_query_filters(query=query,
                                          search_filter_data=table.query_data)

    # noinspection PyMethodMayBeStatic
    def pod_dashboard_view_menu(self):
        return []

    def pod_report_menu(self):
        return [MenuItem(f'advanced_report_builder:kanban_modal,pk-{self.chart_report.id}',
                         menu_display='Edit',
                         font_awesome='fas fa-pencil-alt', css_classes=['btn-primary']),
                *self.duplicate_menu(request=self.request, report_id=self.chart_report.id)
                ]

    def pod_dashboard_edit_menu(self):
        return [MenuItem(f'advanced_report_builder:dashboard_report_modal,pk-{self.dashboard_report.id}',
                         menu_display='Edit',
                         font_awesome='fas fa-pencil-alt', css_classes=['btn-primary'])]

    # noinspection PyMethodMayBeStatic
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
                   'notes',
                   'report_tags']

    def form_setup(self, form, *_args, **_kwargs):
        org_id = self.object.id if hasattr(self, 'object') else None
        form.fields['notes'].widget.attrs['rows'] = 3
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
            self.modal_redirect(self.request.resolver_match.view_name, slug=f'pk-{self.object.id}-new-True')
        else:
            url_name = getattr(settings, 'REPORT_BUILDER_DETAIL_URL_NAME')
            if url_name is not None and self.slug.get('new'):
                url = reverse(url_name, kwargs={'slug': self.object.slug})
                self.command_response('redirect', url=url)


class KanbanLaneModal(QueryBuilderModalBase):
    template_name = 'advanced_report_builder/kanban/modal.html'
    size = 'xl'
    process = PROCESS_EDIT_DELETE
    permission_delete = PERMISSION_OFF
    model = KanbanReportLane

    widgets = {'report_tags': Select2Multiple,
               'order_by_ascending': RBToggle}

    form_fields = ['name',
                   'report_type',
                   'heading_field',
                   'order_by_field',
                   'order_by_ascending',
                   'description',
                   'query_data']

    def form_setup(self, form, *_args, **_kwargs):
        heading_fields = []
        if 'data' in _kwargs:
            heading_field = _kwargs['data'].get('heading_field')
        else:
            heading_field = form.instance.heading_field
        if heading_field:
            form.fields['heading_field'].initial = heading_field
            base_model = form.instance.report_type.content_type.model_class()
            report_builder_fields = getattr(base_model, form.instance.report_type.report_builder_class_name, None)
            self._get_fields(base_model=base_model,
                             fields=heading_fields,
                             report_builder_class=report_builder_fields,
                             selected_field_id=heading_field,
                             for_select2=True)
        form.fields['heading_field'].widget = Select2(attrs={'ajax': True})
        form.fields['heading_field'].widget.select_data = heading_fields

        order_by_fields = []
        if 'data' in _kwargs:
            order_by_field = _kwargs['data'].get('order_by_field')
        else:
            order_by_field = form.instance.order_by_field
        if order_by_field:
            form.fields['order_by_field'].initial = order_by_field
            base_model = form.instance.report_type.content_type.model_class()
            report_builder_fields = getattr(base_model, form.instance.report_type.report_builder_class_name, None)
            self._get_date_fields(base_model=base_model,
                                  fields=order_by_fields,
                                  report_builder_class=report_builder_fields,
                                  selected_field_id=order_by_field)
        form.fields['order_by_field'].widget = Select2(attrs={'ajax': True})
        form.fields['order_by_field'].widget.select_data = order_by_fields

        form.fields['description'].widget = DataMergeWidget()

        return ('name',
                'report_type',
                'heading_field',
                'order_by_field',
                'order_by_ascending',
                'description',
                FieldEx('query_data',
                        template='advanced_report_builder/query_builder.html'),
                )

    def select2_heading_field(self, **kwargs):
        fields = []
        if kwargs['report_type'] != '':
            report_builder_fields, base_model = self.get_report_builder_class(report_type_id=kwargs['report_type'])
            fields = []
            self._get_fields(base_model=base_model,
                             fields=fields,
                             report_builder_class=report_builder_fields,
                             for_select2=True,
                             search_string=kwargs.get('search'))

        return JsonResponse({'results': fields})

    def select2_order_by_field(self, **kwargs):
        fields = []
        if kwargs['report_type'] != '':
            report_builder_fields, base_model = self.get_report_builder_class(report_type_id=kwargs['report_type'])
            fields = []
            self._get_date_fields(base_model=base_model,
                                  fields=fields,
                                  report_builder_class=report_builder_fields,
                                  search_string=kwargs.get('search'))
        return JsonResponse({'results': fields})

    def ajax_get_data_merge_menu(self, **kwargs):
        field_auto_id = kwargs['field_auto_id']
        menus = []
        if kwargs['report_type'] != '':
            report_builder_class, base_model = self.get_report_builder_class(report_type_id=kwargs['report_type'])

            get_menu_fields(base_model=base_model,
                            report_builder_class=report_builder_class,
                            menus=menus)

            menus = [{'code': 'data_merge',
                      'text': 'Data Merge',
                      'menu': menus}]

        return self.command_response(f'build_data_merge_menu_{field_auto_id}',
                                     data=json.dumps(menus))

    def form_valid(self, form):
        form.save()
        return self.command_response('reload')
