import json

from django.forms import CharField, ChoiceField
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django_datatables.columns import ColumnBase, MenuColumn
from django_datatables.helpers import DUMMY_ID
from django_datatables.widgets import DataTableWidget
from django_menus.menu import HtmlMenu, MenuItem
from django_modals.fields import FieldEx
from django_modals.modals import ModelFormModal
from django_modals.processes import PERMISSION_OFF, PROCESS_EDIT_DELETE
from django_modals.widgets.select2 import Select2Multiple
from django_modals.widgets.widgets import Toggle

from advanced_report_builder.columns import ReportBuilderNumberColumn
from advanced_report_builder.globals import ANNOTATION_CHOICE_SUM
from advanced_report_builder.models import MultiCellStyle, MultiValueReport, MultiValueReportCell, ReportType
from advanced_report_builder.toggle import RBToggle
from advanced_report_builder.utils import crispy_modal_link_args, get_report_builder_class
from advanced_report_builder.variable_date import VariableDate
from advanced_report_builder.views.charts_base import ChartJSTable
from advanced_report_builder.views.modals_base import QueryBuilderModalBase
from advanced_report_builder.views.query_modal.mixin import MultiQueryModalMixin
from advanced_report_builder.views.value_base import ValueBaseView
from advanced_report_builder.widgets import SmallNumberInputWidget


class MultiValueModal(ModelFormModal):
    size = 'xl'
    process = PROCESS_EDIT_DELETE
    permission_delete = PERMISSION_OFF
    model = MultiValueReport
    widgets = {
        'report_tags': Select2Multiple,
        'rows': SmallNumberInputWidget,
        'columns': SmallNumberInputWidget,
    }
    ajax_commands = ['datatable', 'button']

    form_fields = ['name', 'notes', 'report_tags', 'rows', 'columns']

    def form_setup(self, form, *_args, **_kwargs):
        org_id = self.object.id if hasattr(self, 'object') else None
        if org_id is not None:
            cell_styles_menu_items = [
                MenuItem(
                    f'advanced_report_builder:multi_value_cell_style_modal,pk-{DUMMY_ID}',
                    menu_display='Edit',
                    css_classes='btn btn-sm btn-outline-dark',
                    font_awesome='fas fa-pencil',
                ),
            ]

            form.fields['cell_styles'] = CharField(
                required=False,
                label='Cell Styles',
                widget=DataTableWidget(
                    model=MultiCellStyle,
                    fields=[
                        '_.index',
                        '.id',
                        ColumnBase(column_name='cell_style_name', field='name', title='Name'),
                        MenuColumn(
                            column_name='menu',
                            field='id',
                            column_defs={'orderable': False, 'className': 'dt-right'},
                            menu=HtmlMenu(self.request, 'button_group').add_items(*cell_styles_menu_items),
                        ),
                    ],
                    attrs={'filter': {'multi_value_report__id': self.object.id}},
                ),
            )
            cells_menu_items = [
                MenuItem(
                    f'advanced_report_builder:multi_value_cell_modal,pk-{DUMMY_ID}',
                    menu_display='Edit',
                    css_classes='btn btn-sm btn-outline-dark',
                    font_awesome='fas fa-pencil',
                ),
            ]

            form.fields['cells'] = CharField(
                required=False,
                label='Cell Styles',
                widget=DataTableWidget(
                    model=MultiValueReportCell,
                    fields=[
                        '_.index',
                        '.id',
                        # 'multi_value_type',
                        'row',
                        'column',
                        MenuColumn(
                            column_name='menu',
                            field='id',
                            column_defs={'orderable': False, 'className': 'dt-right'},
                            menu=HtmlMenu(self.request, 'button_group').add_items(*cells_menu_items),
                        ),
                    ],
                    attrs={'filter': {'report__id': self.object.id}},
                ),
            )

            return [
                *self.form_fields,
                crispy_modal_link_args(
                    'advanced_report_builder:multi_value_cell_style_modal',
                    'Add Cell Style',
                    'multi_value_report_id-',
                    self.object.id,
                    div=True,
                    div_classes='form-buttons',
                    button_classes='btn btn-primary',
                    font_awesome='fa fa-plus',
                ),
                'cell_styles',
                crispy_modal_link_args(
                    'advanced_report_builder:multi_value_cell_modal',
                    'Add Cell Data',
                    'report_id-',
                    self.object.id,
                    div=True,
                    div_classes='form-buttons',
                    button_classes='btn btn-primary',
                    font_awesome='fa fa-plus',
                ),
                'cells',
            ]


class MultiValueCellStyleModal(ModelFormModal):
    size = 'xl'
    process = PROCESS_EDIT_DELETE
    permission_delete = PERMISSION_OFF
    model = MultiCellStyle

    widgets = {
        'bold': RBToggle,
        'italic': RBToggle,
        'font_size': SmallNumberInputWidget,
    }

    form_fields = ['name', 'bold', 'italic', 'font_size', 'background_colour']


class MultiValueReportCellModal(MultiQueryModalMixin, QueryBuilderModalBase):
    size = 'xl'
    process = PROCESS_EDIT_DELETE
    permission_delete = PERMISSION_OFF
    model = MultiValueReportCell

    form_fields = [
        'multi_value_type',
        'text',
        'row',
        'column',
        'col_span',
        'row_span',
        'report_type',
        'field',
        'numerator',
        'prefix',
        'decimal_places',
        'show_breakdown',
        'breakdown_fields',
        'average_scale',
        'average_start_period',
        'average_end_period',
    ]

    widgets = {
        'report_tags': Select2Multiple,
        'show_breakdown': Toggle(attrs={'data-onstyle': 'success', 'data-on': 'YES', 'data-off': 'NO'}),
        'row': SmallNumberInputWidget,
        'column': SmallNumberInputWidget,
        'col_span': SmallNumberInputWidget,
        'row_span': SmallNumberInputWidget,
        'decimal_places': SmallNumberInputWidget,
    }

    def form_setup(self, form, *_args, **_kwargs):
        form.add_trigger(
            'multi_value_type',
            'onchange',
            [
                {
                    'selector': '#div_id_text',
                    'values': {
                        MultiValueReportCell.MultiValueType.STATIC_TEXT: 'show',
                    },
                    'default': 'hide',
                },
                {
                    'selector': '#div_id_field',
                    'values': {
                        MultiValueReportCell.MultiValueType.STATIC_TEXT: 'hide',
                        MultiValueReportCell.MultiValueType.COUNT: 'hide',
                        MultiValueReportCell.MultiValueType.PERCENT_FROM_COUNT: 'hide',
                    },
                    'default': 'show',
                },
                {
                    'selector': '#div_id_prefix',
                    'values': {
                        MultiValueReportCell.MultiValueType.STATIC_TEXT: 'hide',
                        MultiValueReportCell.MultiValueType.COUNT: 'hide',
                        MultiValueReportCell.MultiValueType.PERCENT_FROM_COUNT: 'hide',
                    },
                    'default': 'show',
                },
                {
                    'selector': '#div_id_numerator',
                    'values': {MultiValueReportCell.MultiValueType.PERCENT: 'show'},
                    'default': 'hide',
                },
                {
                    'selector': 'label[for=id_field]',
                    'values': {
                        MultiValueReportCell.MultiValueType.PERCENT: (
                            'html',
                            'Denominator field',
                        )
                    },
                    'default': ('html', 'Field'),
                },
                {
                    'selector': '#div_id_average_scale',
                    'values': {MultiValueReportCell.MultiValueType.AVERAGE_SUM_OVER_TIME: 'show'},
                    'default': 'hide',
                },
                {
                    'selector': '#div_id_average_start_period',
                    'values': {MultiValueReportCell.MultiValueType.AVERAGE_SUM_OVER_TIME: 'show'},
                    'default': 'hide',
                },
                {
                    'selector': '#div_id_average_end_period',
                    'values': {MultiValueReportCell.MultiValueType.AVERAGE_SUM_OVER_TIME: 'show'},
                    'default': 'hide',
                },
                {
                    'selector': '#div_id_report_type',
                    'values': {
                        MultiValueReportCell.MultiValueType.STATIC_TEXT: 'hide',
                    },
                    'default': 'show',
                },
                {
                    'selector': '#div_id_decimal_places',
                    'values': {
                        MultiValueReportCell.MultiValueType.STATIC_TEXT: 'hide',
                    },
                    'default': 'show',
                },
                {
                    'selector': '#div_id_show_breakdown',
                    'values': {
                        MultiValueReportCell.MultiValueType.STATIC_TEXT: 'hide',
                    },
                    'default': 'show',
                },
            ],
        )

        form.add_trigger(
            'show_breakdown',
            'onchange',
            [
                {
                    'selector': '#div_id_breakdown_fields',
                    'values': {'checked': 'show'},
                    'default': 'hide',
                },
            ],
        )
        if 'data' in _kwargs and len(_kwargs['data']) > 0:
            field = _kwargs['data'].get('field')
            numerator = _kwargs['data'].get('numerator')
            report_type_id = _kwargs['data'].get('report_type')
            if report_type_id != '':
                report_type = get_object_or_404(ReportType, id=report_type_id)
            else:
                report_type = form.instance.report_type
        else:
            field = form.instance.field
            report_type = form.instance.report_type
            numerator = form.instance.numerator

        self.setup_field(
            field_type='number',
            form=form,
            field_name='field',
            selected_field_id=field,
            report_type=report_type,
        )

        self.setup_field(
            field_type='number',
            form=form,
            field_name='numerator',
            selected_field_id=numerator,
            report_type=report_type,
        )

        url = reverse(
            'advanced_report_builder:single_value_field_modal',
            kwargs={'slug': 'selector-99999-data-FIELD_INFO-report_type_id-REPORT_TYPE_ID'},
        )

        range_type_choices = VariableDate.RANGE_TYPE_CHOICES
        form.fields['average_start_period'] = ChoiceField(required=False, choices=range_type_choices)
        form.fields['average_end_period'] = ChoiceField(required=False, choices=range_type_choices)
        fields = [
            'multi_value_type',
            'text',
            'row',
            'column',
            'col_span',
            'row_span',
            'report_type',
            'field',
            'numerator',
            'prefix',
            'decimal_places',
            'show_breakdown',
            'average_scale',
            'average_start_period',
            'average_end_period',
            FieldEx(
                'breakdown_fields',
                template='advanced_report_builder/select_column.html',
                extra_context={'select_column_url': url, 'command_prefix': ''},
            ),
        ]
        return fields

    def select2_field(self, **kwargs):
        return self.get_fields_for_select2(
            field_type='number',
            report_type=kwargs['report_type'],
            search_string=kwargs.get('search'),
        )

    def select2_numerator(self, **kwargs):
        return self.get_fields_for_select2(
            field_type='number',
            report_type=kwargs['report_type'],
            search_string=kwargs.get('search'),
        )

    def ajax_get_fields(self, **kwargs):
        report_type_id = kwargs['report_type']
        report_builder_fields, base_model = self.get_report_builder_class(report_type_id=report_type_id)
        fields = []
        tables = []
        self._get_fields(
            base_model=base_model,
            fields=fields,
            tables=tables,
            report_builder_class=report_builder_fields,
        )
        return self.command_response('report_fields', data=json.dumps({'fields': fields, 'tables': tables}))

    def form_valid(self, form):
        chart_report = form.save(commit=False)
        chart_report._current_user = self.request.user
        chart_report.save()
        return self.command_response('reload')


class MultiValueView(ValueBaseView):
    number_field = ReportBuilderNumberColumn
    template_name = 'advanced_report_builder/multi_values/report.html'
    chart_js_table = ChartJSTable

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
        self.chart_report = self.report.multivaluereport
        self.dashboard_report = kwargs.get('dashboard_report')
        self.enable_edit = kwargs.get('enable_edit')
        return super().dispatch(request, *args, **kwargs)

    def pod_dashboard_view_menu(self):
        return []

    def pod_report_menu(self):
        return [
            MenuItem(
                f'advanced_report_builder:multi_value_modal,pk-{self.chart_report.id}',
                menu_display='Edit',
                font_awesome='fas fa-pencil-alt',
                css_classes=['btn-primary'],
            ),
            *self.duplicate_menu(request=self.request, report_id=self.chart_report.id),
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs) if hasattr(super(), 'get_context_data') else {}

        multi_value_report_cells = MultiValueReportCell.objects.filter(report=self.chart_report).order_by(
            'row', 'column'
        )

        table_data = [[None for _ in range(self.chart_report.columns)] for _ in range(self.chart_report.rows)]

        for multi_value_report_cell in multi_value_report_cells:
            base_model = multi_value_report_cell.get_base_model()
            value = ''
            report_builder_class = None

            row = multi_value_report_cell.row - 1
            column = multi_value_report_cell.column - 1
            if table_data[row][column] is not None:
                continue

            multi_value_type = multi_value_report_cell.multi_value_type
            if base_model is not None:
                report_builder_class = get_report_builder_class(
                    model=base_model, report_type=multi_value_report_cell.report_type
                )

            fields = []
            if multi_value_type == MultiValueReportCell.MultiValueType.STATIC_TEXT:
                value = multi_value_report_cell.text
            elif multi_value_type == MultiValueReportCell.MultiValueType.COUNT:
                self._get_count(fields=fields)
            elif multi_value_type == MultiValueReportCell.MultiValueType.SUM:
                self._process_aggregations(
                    field=multi_value_report_cell.field,
                    report_builder_class=report_builder_class,
                    base_model=base_model,
                    decimal_places=multi_value_report_cell.decimal_places,
                    fields=fields,
                    aggregations_type=ANNOTATION_CHOICE_SUM,
                )

            if fields:
                value = self.render_value(base_model=base_model, fields=fields)

            table_data[row][column] = {'value': value, 'cell': multi_value_report_cell}

            if multi_value_report_cell.row_span > 1 or multi_value_report_cell.col_span > 1:
                for row_offset in range(multi_value_report_cell.row_span):
                    for col_offset in range(multi_value_report_cell.col_span):
                        # skip the main (top-left) cell
                        if row_offset == 0 and col_offset == 0:
                            continue

                        table_data[row + row_offset][column + col_offset] = {'value': None}

        context['html'] = self.render_html(table_data=table_data)
        return context

    @staticmethod
    def render_html(table_data):
        html = '<table class="table table-bordered kanban_summary">'
        for row in table_data:
            html += '<tr>'
            for cell in row:
                if cell is None:
                    html += '<td></td>'
                elif cell['value'] is not None:
                    attrs = ''
                    multi_value_report_cell = cell['cell']
                    col_span = multi_value_report_cell.col_span
                    row_span = multi_value_report_cell.row_span
                    if col_span > 1:
                        attrs += f' colspan="{col_span}"'
                    if row_span > 1:
                        attrs += f' colspan="{row_span}"'
                    value = cell['value']
                    html += f'<td{attrs}>{value}</td>'
            html += '</tr>'

        html += '</table>'
        return html

    def pod_dashboard_edit_menu(self):
        return [
            MenuItem(
                f'advanced_report_builder:dashboard_report_modal,pk-{self.dashboard_report.id}',
                menu_display='Edit',
                font_awesome='fas fa-pencil-alt',
                css_classes=['btn-primary'],
            )
        ]

    def render_value(self, base_model, fields):
        table = self.chart_js_table(model=base_model)
        table.add_columns(*fields)
        table.single_value = self.chart_report
        table.enable_links = self.kwargs.get('enable_links')
        table.datatable_template = 'advanced_report_builder/multi_values/middle.html'
        value = table.render()
        return value
