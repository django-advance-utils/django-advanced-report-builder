import json
from datetime import timedelta

from ajax_helpers.utils import random_string
from django.conf import settings
from django.forms import CharField, ModelChoiceField, NumberInput
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import TemplateView
from django_datatables.columns import DateColumn, MenuColumn
from django_datatables.datatables import DatatableExcludedRow
from django_datatables.helpers import DUMMY_ID, row_link
from django_datatables.widgets import DataTableReorderWidget
from django_menus.menu import HtmlMenu, MenuItem
from django_modals.fields import FieldEx
from django_modals.form_helpers import HorizontalNoEnterHelper
from django_modals.helper import modal_button, modal_button_method
from django_modals.modals import Modal, ModelFormModal
from django_modals.processes import PERMISSION_OFF, PROCESS_EDIT_DELETE
from django_modals.widgets.select2 import Select2, Select2Multiple

from advanced_report_builder.columns import ReportBuilderNumberColumn
from advanced_report_builder.data_merge.utils import DataMergeUtils
from advanced_report_builder.data_merge.widget import DataMergeWidget
from advanced_report_builder.filter_query import FilterQueryMixin
from advanced_report_builder.models import (
    CalendarReport,
    CalendarReportDataSet,
    CalendarReportDescription,
    ReportType,
)
from advanced_report_builder.utils import crispy_modal_link_args, get_report_builder_class
from advanced_report_builder.views.charts_base import ChartJSTable
from advanced_report_builder.views.datatables.utils import DescriptionColumn
from advanced_report_builder.views.helpers import QueryBuilderModelForm
from advanced_report_builder.views.modals_base import QueryBuilderModalBase
from advanced_report_builder.views.report import ReportBase


class CalendarTable(ChartJSTable):
    def get_table_array(self, request, results):
        result_processes = self.get_result_processes()
        for p in result_processes:
            p.setup_results(request, self.page_results)
        for c in self.columns:
            c.setup_results(request, self.page_results)
        results_list = []
        for data_dict in results:
            try:
                for p in result_processes:
                    p.row_result(data_dict, self.page_results)
                row_data = []
                for column in self.columns:
                    if isinstance(column, DescriptionColumn):
                        row_data.append(column.row_result(data_dict, self.page_results, columns=self.columns))
                    else:
                        row_data.append(column.row_result(data_dict, self.page_results))

                results_list.append(row_data)
            except DatatableExcludedRow:
                pass
        return results_list


class CalendarView(DataMergeUtils, ReportBase, FilterQueryMixin, TemplateView):
    number_field = ReportBuilderNumberColumn
    template_name = 'advanced_report_builder/calendar/report.html'
    chart_js_table = CalendarTable

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
            *self.queries_menu(report=self.report, dashboard_report=self.dashboard_report),
        )

    def dispatch(self, request, *args, **kwargs):
        self.report = kwargs.get('report')
        self.chart_report = self.report.calendarreport
        self.dashboard_report = kwargs.get('dashboard_report')
        self.enable_edit = kwargs.get('enable_edit')
        return super().dispatch(request, *args, **kwargs)

    def view_filter_extra(self, query, table):
        if table.extra_query_filter:
            query = query.filter(table.extra_query_filter)
        return self.view_filter(query, table)

    def get_calendar_events(self, base_model, calendar_report_data_set, lanes, label=None, extra_query_filter=None):
        table = self.chart_js_table(model=base_model)

        report_builder_class = get_report_builder_class(
            model=base_model, report_type=calendar_report_data_set.report_type
        )
        table_indexes = ['start_date_field', 'end_date_field']
        table.add_columns(calendar_report_data_set.start_date_field)
        if calendar_report_data_set.end_date_type == CalendarReportDataSet.END_DATE_TYPE_FIELD:
            table.add_columns(calendar_report_data_set.end_date_field)
        elif calendar_report_data_set.end_date_type == CalendarReportDataSet.END_DATE_TYPE_DURATION_FIELD:
            _, _, _, start_field_col_field = self.get_field_details(
                base_model=base_model,
                field=calendar_report_data_set.start_date_field,
                report_builder_class=report_builder_class,
            )
            _, _, _, end_duration_col_field = self.get_field_details(
                base_model=base_model,
                field=calendar_report_data_set.end_duration_field,
                report_builder_class=report_builder_class,
            )

            class DurationEndDateColumn(DateColumn):
                def col_setup(self):
                    self.field = [start_field_col_field, end_duration_col_field]

                def row_result(self, data, _page_result):
                    start_date = data.get(self.model_path + start_field_col_field)
                    end_duration = data.get(self.model_path + end_duration_col_field)
                    if end_duration is None or end_duration <= 0:
                        end_duration = 3600
                    end_date = start_date + timedelta(seconds=end_duration)
                    try:
                        date = end_date.strftime('%d/%m/%Y')
                        time_str = end_date.strftime('%H:%M')
                        return date + ' ' + time_str
                    except AttributeError:
                        return ''

            table.add_columns(DurationEndDateColumn(column_name='EndDate'))

        elif calendar_report_data_set.end_date_type == CalendarReportDataSet.END_DATE_TYPE_DURATION_FIXED:
            _, _, _, start_field_col_field = self.get_field_details(
                base_model=base_model,
                field=calendar_report_data_set.start_date_field,
                report_builder_class=report_builder_class,
            )

            class FixedDurationEndDateColumn(DateColumn):
                def row_result(self, data, _page_result):
                    start_date = data.get(self.model_path + start_field_col_field)
                    end_date = start_date + timedelta(seconds=calendar_report_data_set.end_duration)
                    try:
                        date = end_date.strftime('%d/%m/%Y')
                        time_str = end_date.strftime('%H:%M')
                        return date + ' ' + time_str
                    except AttributeError:
                        return ''

            table.add_columns(FixedDurationEndDateColumn(column_name='EndDate'))

        if (
            calendar_report_data_set.display_type
            in (
                CalendarReportDataSet.DISPLAY_TYPE_NAME_AND_DESCRIPTION,
                CalendarReportDataSet.DISPLAY_TYPE_HEADING_ONLY,
            )
            and calendar_report_data_set.heading_field is not None
        ):
            table_indexes.append('heading')
            table.add_columns(calendar_report_data_set.heading_field)

        if calendar_report_data_set.background_colour_field is not None:
            table_indexes.append('background_colour')
            table.add_columns(calendar_report_data_set.background_colour_field)

        if (
            calendar_report_data_set.display_type
            in (
                CalendarReportDataSet.DISPLAY_TYPE_NAME_AND_DESCRIPTION,
                CalendarReportDataSet.DISPLAY_TYPE_DESCRIPTION_ONLY,
            )
            and calendar_report_data_set.calendar_report_description is not None
        ):
            description = calendar_report_data_set.calendar_report_description.description
            columns, column_map = self.get_data_merge_columns(
                base_model=base_model, report_builder_class=report_builder_class, html=description, table=table
            )
            description_column_name = (
                'description'
                if calendar_report_data_set.display_type == CalendarReportDataSet.DISPLAY_TYPE_NAME_AND_DESCRIPTION
                else 'heading'
            )
            table_indexes.append(description_column_name)
            table.add_columns(
                DescriptionColumn(
                    column_name=description_column_name, field='', html=description, column_map=column_map
                )
            )
            table.add_columns(*columns)

        table.table_options['indexes'] = table_indexes

        if calendar_report_data_set.link_field and self.kwargs.get('enable_links'):
            _, col_type_override, _, _ = self.get_field_details(
                base_model=base_model,
                field=calendar_report_data_set.link_field,
                report_builder_class=report_builder_class,
            )
            field = col_type_override.field[0] if isinstance(col_type_override.field, list) else 'id'
            if field not in table.columns:
                table.add_columns(f'.{field}')
            table.has_link = True
            table.table_options['row_href'] = row_link(col_type_override.url, field)
        else:
            table.has_link = False

        table.datatable_template = 'advanced_report_builder/calendar/middle.html'

        table.query_data = calendar_report_data_set.query_data
        table.extra_query_filter = extra_query_filter
        table.view_filter = self.view_filter_extra
        lanes.append({'datatable': table, 'label': label, 'calendar_report_data_set': calendar_report_data_set})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = self.get_title()
        calendar_report_data_sets = self.chart_report.calendarreportdataset_set.all()
        lanes = []
        headings = []

        for calendar_report_data_set in calendar_report_data_sets:
            base_model = calendar_report_data_set.get_base_model()
            self.get_calendar_events(
                base_model=base_model, calendar_report_data_set=calendar_report_data_set, lanes=lanes
            )
        view_type = None
        if self.dashboard_report and self.dashboard_report.options is not None:
            view_type = self.dashboard_report.options.get('calendar_view_type')
            if view_type is not None:
                view_type = int(view_type)

        context['view_type'] = self.chart_report.get_view_type_for_calendar(view_type=view_type)
        context['calendar_report'] = self.chart_report
        context['headings'] = headings
        context['lanes'] = lanes
        context['field_id'] = random_string()
        return context

    def view_filter(self, query, table):
        if not table.query_data:
            return query

        return self.process_query_filters(query=query, search_filter_data=table.query_data)

    # noinspection PyMethodMayBeStatic
    def pod_dashboard_view_menu(self):
        return []

    def pod_report_menu(self):
        return [
            MenuItem(
                f'advanced_report_builder:calendar_modal,pk-{self.chart_report.id}',
                menu_display='Edit',
                font_awesome='fas fa-pencil-alt',
                css_classes=['btn-primary'],
            ),
            *self.duplicate_menu(request=self.request, report_id=self.chart_report.id),
        ]

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
    def queries_menu(self, report, dashboard_report):
        return []


class CalendarModal(ModelFormModal):
    size = 'xl'
    process = PROCESS_EDIT_DELETE
    permission_delete = PERMISSION_OFF
    model = CalendarReport
    widgets = {'report_tags': Select2Multiple}
    ajax_commands = ['datatable', 'button']

    form_fields = ['name', 'notes', 'report_tags', 'height', 'view_type']

    def form_setup(self, form, *_args, **_kwargs):
        org_id = self.object.id if hasattr(self, 'object') else None
        form.fields['notes'].widget.attrs['rows'] = 3

        if org_id is not None:
            lane_menu_items = [
                MenuItem(
                    f'advanced_report_builder:calendar_data_set_duplicate_modal,pk-{DUMMY_ID}',
                    menu_display='Duplicate',
                    css_classes='btn btn-sm btn-outline-dark',
                    font_awesome='fas fa-clone',
                ),
                MenuItem(
                    f'advanced_report_builder:calendar_data_set_modal,pk-{DUMMY_ID}',
                    menu_display='Edit',
                    css_classes='btn btn-sm btn-outline-dark',
                    font_awesome='fas fa-pencil',
                ),
            ]

            form.fields['data_sets'] = CharField(
                required=False,
                label='Data Sets',
                widget=DataTableReorderWidget(
                    model=CalendarReportDataSet,
                    order_field='order',
                    fields=[
                        '_.index',
                        '.id',
                        'name',
                        MenuColumn(
                            column_name='menu',
                            field='id',
                            column_defs={'orderable': False, 'className': 'dt-right'},
                            menu=HtmlMenu(self.request, 'button_group').add_items(*lane_menu_items),
                        ),
                    ],
                    attrs={'filter': {'calendar_report__id': self.object.id}},
                ),
            )

            description_menu_items = [
                MenuItem(
                    f'advanced_report_builder:calendar_description_duplicate_modal,pk-{DUMMY_ID}',
                    menu_display='Duplicate',
                    css_classes='btn btn-sm btn-outline-dark',
                    font_awesome='fas fa-clone',
                ),
                MenuItem(
                    f'advanced_report_builder:calendar_description_modal,pk-{DUMMY_ID}',
                    menu_display='Edit',
                    css_classes='btn btn-sm btn-outline-dark',
                    font_awesome='fas fa-pencil',
                ),
            ]

            form.fields['descriptions'] = CharField(
                required=False,
                label='Descriptions',
                widget=DataTableReorderWidget(
                    model=CalendarReportDescription,
                    order_field='order',
                    fields=[
                        '_.index',
                        '.id',
                        'name',
                        MenuColumn(
                            column_name='menu',
                            field='id',
                            column_defs={'orderable': False, 'className': 'dt-right'},
                            menu=HtmlMenu(self.request, 'button_group').add_items(*description_menu_items),
                        ),
                    ],
                    attrs={'filter': {'calendar_report__id': self.object.id}},
                ),
            )

            modal_button('Custom Close', 'close', 'btn-warning')

            return [
                *self.form_fields,
                crispy_modal_link_args(
                    'advanced_report_builder:calendar_data_set_modal',
                    'Add Data Set',
                    'calendar_report_id-',
                    self.object.id,
                    div=True,
                    div_classes='form-buttons',
                    button_classes='btn btn-primary',
                    font_awesome='fa fa-plus',
                ),
                'data_sets',
                crispy_modal_link_args(
                    'advanced_report_builder:calendar_description_modal',
                    'Add Description',
                    'calendar_report_id-',
                    self.object.id,
                    div=True,
                    div_classes='form-buttons',
                    button_classes='btn btn-primary',
                    font_awesome='fa fa-plus',
                ),
                'descriptions',
            ]

    def datatable_sort(self, **kwargs):
        form = self.get_form()
        widget = form.fields[kwargs['table_id'][3:]].widget
        _model = widget.attrs['table_model']
        current_sort = dict(_model.objects.filter(calendar_report=self.object.id).values_list('id', 'order'))
        for s in kwargs['sort']:
            if current_sort[s[1]] != s[0]:
                o = _model.objects.get(id=s[1])
                o.order = s[0]
                o.save()
        return self.command_response('')

    def post_save(self, created, form):
        if created:
            self.modal_redirect(self.request.resolver_match.view_name, slug=f'pk-{self.object.id}-new-True')
        else:
            url_name = getattr(settings, 'REPORT_BUILDER_DETAIL_URL_NAME', '')
            if url_name and self.slug.get('new'):
                url = reverse(url_name, kwargs={'slug': self.object.slug})
                self.command_response('redirect', url=url)


class CalendarDataSetForm(QueryBuilderModelForm):
    cancel_class = 'btn-secondary modal-cancel'

    class DurationWidget(NumberInput):
        crispy_kwargs = {'appended_text': 'Seconds', 'input_size': 'input-group-sm'}

    class Meta:
        model = CalendarReportDataSet
        fields = [
            'name',
            'report_type',
            'display_type',
            'heading_field',
            'calendar_report_description',
            'background_colour_field',
            'link_field',
            'start_date_field',
            'end_date_type',
            'end_date_field',
            'end_duration_field',
            'end_duration',
            'query_data',
        ]
        widgets = {
            'display_type': Select2,
            'end_date_type': Select2,
        }

    end_duration = CharField(widget=DurationWidget)


class CalendarDataSetModal(QueryBuilderModalBase):
    template_name = 'advanced_report_builder/calendar/modal.html'
    size = 'xl'
    process = PROCESS_EDIT_DELETE
    permission_delete = PERMISSION_OFF
    model = CalendarReportDataSet
    helper_class = HorizontalNoEnterHelper
    form_class = CalendarDataSetForm

    def form_setup(self, form, *_args, **_kwargs):
        if 'data' in _kwargs:
            heading_field = _kwargs['data'].get('heading_field')
            start_date_field = _kwargs['data'].get('start_date_field')
            end_date_field = _kwargs['data'].get('end_date_field')
            end_duration_field = _kwargs['data'].get('end_duration_field')
            report_type_id = _kwargs['data'].get('report_type')
            background_colour_field = _kwargs['data'].get('background_colour_field')
            link_field = _kwargs['data'].get('link_field')
            calendar_report_description = CalendarReportDescription.objects.filter(
                pk=_kwargs['data'].get('calendar_report_description')
            ).first()
            report_type = get_object_or_404(ReportType, id=report_type_id)

        else:
            heading_field = form.instance.heading_field
            report_type = form.instance.report_type
            start_date_field = form.instance.start_date_field
            end_date_field = form.instance.end_date_field
            end_duration_field = form.instance.end_duration_field
            background_colour_field = form.instance.background_colour_field
            link_field = form.instance.link_field
            calendar_report_description = form.instance.calendar_report_description

        form.fields['calendar_report_description'].widget = Select2(attrs={'ajax': True})
        if calendar_report_description is not None:
            form.fields['calendar_report_description'].widget.select_data = [
                {'id': calendar_report_description.id, 'text': calendar_report_description.name}
            ]
        form.fields['calendar_report_description'].label = 'Description'
        form.fields['calendar_report_description'].required = False

        form.fields['report_type'] = ModelChoiceField(queryset=ReportType.objects.all(), widget=Select2, required=False)

        form.add_trigger(
            'display_type',
            'onchange',
            [
                {
                    'selector': '#div_id_calendar_report_description',
                    'values': {CalendarReportDataSet.DISPLAY_TYPE_HEADING_ONLY: 'hide'},
                    'default': 'show',
                },
                {
                    'selector': '#div_id_heading_field',
                    'values': {CalendarReportDataSet.DISPLAY_TYPE_DESCRIPTION_ONLY: 'hide'},
                    'default': 'show',
                },
            ],
        )
        form.add_trigger(
            'end_date_type',
            'onchange',
            [
                {
                    'selector': '#div_id_end_date_field',
                    'values': {CalendarReportDataSet.END_DATE_TYPE_FIELD: 'show'},
                    'default': 'hide',
                },
                {
                    'selector': '#div_id_end_duration_field',
                    'values': {CalendarReportDataSet.END_DATE_TYPE_DURATION_FIELD: 'show'},
                    'default': 'hide',
                },
                {
                    'selector': '#div_id_end_duration',
                    'values': {CalendarReportDataSet.END_DATE_TYPE_DURATION_FIXED: 'show'},
                    'default': 'hide',
                },
            ],
        )
        self.setup_field(
            field_type='all',
            form=form,
            field_name='heading_field',
            selected_field_id=heading_field,
            report_type=report_type,
        )

        self.setup_field(
            field_type='date',
            form=form,
            field_name='start_date_field',
            selected_field_id=start_date_field,
            report_type=report_type,
        )

        self.setup_field(
            field_type='date',
            form=form,
            field_name='end_date_field',
            selected_field_id=end_date_field,
            report_type=report_type,
        )

        self.setup_field(
            field_type='number',
            form=form,
            field_name='end_duration_field',
            selected_field_id=end_duration_field,
            report_type=report_type,
        )

        self.setup_field(
            field_type='colour',
            form=form,
            field_name='background_colour_field',
            selected_field_id=background_colour_field,
            report_type=report_type,
        )

        self.setup_field(
            field_type='link', form=form, field_name='link_field', selected_field_id=link_field, report_type=report_type
        )

        return (
            'name',
            'report_type',
            'display_type',
            'heading_field',
            'calendar_report_description',
            'start_date_field',
            'end_date_type',
            'end_date_field',
            'end_duration_field',
            'end_duration',
            'background_colour_field',
            'link_field',
            FieldEx('query_data', template='advanced_report_builder/query_builder.html'),
        )

    def select2_heading_field(self, **kwargs):
        return self.get_fields_for_select2(
            field_type='all', report_type=kwargs['report_type'], search_string=kwargs.get('search')
        )

    def select2_order_by_field(self, **kwargs):
        return self.get_fields_for_select2(
            field_type='django_order', report_type=kwargs['report_type'], search_string=kwargs.get('search')
        )

    def select2_start_date_field(self, **kwargs):
        return self.get_fields_for_select2(
            field_type='date', report_type=kwargs['report_type'], search_string=kwargs.get('search')
        )

    def select2_end_date_field(self, **kwargs):
        return self.get_fields_for_select2(
            field_type='date', report_type=kwargs['report_type'], search_string=kwargs.get('search')
        )

    def select2_end_duration_field(self, **kwargs):
        return self.get_fields_for_select2(
            field_type='number', report_type=kwargs['report_type'], search_string=kwargs.get('search')
        )

    def select2_link_field(self, **kwargs):
        return self.get_fields_for_select2(
            field_type='link', report_type=kwargs['report_type'], search_string=kwargs.get('search')
        )

    def select2_background_colour_field(self, **kwargs):
        return self.get_fields_for_select2(
            field_type='colour', report_type=kwargs['report_type'], search_string=kwargs.get('search')
        )

    def select2_calendar_report_description(self, **kwargs):
        descriptions = []
        report_type_id = kwargs['report_type']
        if report_type_id != '':
            calendar_report_id = self.object.calendar_report_id
            _filter = CalendarReportDescription.objects.filter(
                report_type_id=report_type_id, calendar_report_id=calendar_report_id
            )
            search = kwargs.get('search')
            if search:
                _filter = _filter.filter(name__icontains=search)
            for description in _filter.values('id', 'name'):
                descriptions.append({'id': description['id'], 'text': description['name']})

        return JsonResponse({'results': descriptions})

    def form_valid(self, form):
        form.save()
        return self.command_response('reload')


class CalendarDataSetDuplicateModal(Modal):
    def modal_content(self):
        return 'Are you sure you want to duplicate this lane?'

    def get_modal_buttons(self):
        return [modal_button_method('Confirm', 'duplicate'), modal_button('Cancel', 'close', 'btn-secondary')]

    def button_duplicate(self, **_kwargs):
        calendar_report_data_set = get_object_or_404(CalendarReportDataSet, id=self.slug['pk'])
        calendar_report_data_set.pk = None
        calendar_report_data_set.name = f'Copy of {calendar_report_data_set.name}'
        calendar_report_data_set.order = None
        calendar_report_data_set.save()
        return self.command_response('reload')


class CalendarDescriptionModal(DataMergeUtils, QueryBuilderModalBase):
    template_name = 'advanced_report_builder/calendar/description_modal.html'
    size = 'xl'
    process = PROCESS_EDIT_DELETE
    permission_delete = PERMISSION_OFF
    model = CalendarReportDescription

    widgets = {'report_tags': Select2Multiple}

    form_fields = ['name', 'report_type', 'description']

    def form_setup(self, form, *_args, **_kwargs):
        form.fields['description'].widget = DataMergeWidget()

        return ('name', 'report_type', 'description')

    def ajax_get_description_data_merge_menu(self, **kwargs):
        field_auto_id = kwargs['field_auto_id']
        menus = []
        if kwargs['report_type'] != '':
            report_builder_class, base_model = self.get_report_builder_class(report_type_id=kwargs['report_type'])

            self.get_menu_fields(base_model=base_model, report_builder_class=report_builder_class, menus=menus)

            menus = [{'code': 'data_merge', 'text': 'Data Merge', 'menu': menus}]

        return self.command_response(f'build_data_merge_menu_{field_auto_id}', data=json.dumps(menus))

    def form_valid(self, form):
        form.save()
        return self.command_response('reload')


class CalendarDescriptionDuplicateModal(Modal):
    def modal_content(self):
        return 'Are you sure you want to duplicate this description?'

    def get_modal_buttons(self):
        return [modal_button_method('Confirm', 'duplicate'), modal_button('Cancel', 'close', 'btn-secondary')]

    def button_duplicate(self, **_kwargs):
        calendar_report_description = get_object_or_404(CalendarReportDescription, id=self.slug['pk'])
        calendar_report_description.pk = None
        calendar_report_description.name = f'Copy of {calendar_report_description.name}'
        calendar_report_description.save()
        return self.command_response('reload')
