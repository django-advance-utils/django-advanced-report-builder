import copy
import json

from django.forms import CharField, ChoiceField, ModelChoiceField
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django_datatables.columns import ColumnBase, MenuColumn
from django_datatables.helpers import DUMMY_ID
from django_datatables.widgets import DataTableWidget
from django_menus.menu import HtmlMenu, MenuItem
from django_modals.fields import FieldEx
from django_modals.helper import show_modal
from django_modals.modals import Modal, ModelFormModal
from django_modals.processes import PERMISSION_OFF, PROCESS_EDIT_DELETE
from django_modals.widgets.select2 import Select2, Select2Multiple
from django_modals.widgets.widgets import Toggle
from expression_builder.exceptions import ExpressionVariableError
from expression_builder.expression_builder import ExpressionBuilder

from advanced_report_builder.columns import ReportBuilderNumberColumn
from advanced_report_builder.globals import ANNOTATION_CHOICE_AVERAGE_SUM_FROM_COUNT, ANNOTATION_CHOICE_SUM
from advanced_report_builder.models import MultiCellStyle, MultiValueReport, MultiValueReportCell, ReportType
from advanced_report_builder.toggle import RBToggle
from advanced_report_builder.utils import crispy_modal_link_args, get_report_builder_class, excel_column_name
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
                    'advanced_report_builder:multi_value_cells_modal',
                    'Edit Cells',
                    'multi_value_report_id-',
                    self.object.id,
                    div=True,
                    div_classes='form-buttons',
                    button_classes='btn btn-primary',
                    font_awesome='fas fa-edit',
                ),
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
        'align_type': Select2,
    }

    form_fields = ['name', 'align_type', 'bold', 'italic', 'font_size', 'background_colour']


class MultiValueReportCellModal(MultiQueryModalMixin, QueryBuilderModalBase):
    size = 'xl'
    process = PROCESS_EDIT_DELETE
    permission_delete = PERMISSION_OFF
    model = MultiValueReportCell

    @property
    def modal_title(self):

        if self.object.row and self.object.column:
            title = excel_column_name(int(self.object.column), row=int(self.object.row))
        else:
            title = ' value'

        return [f'Add {title}', f'Edit {title}']

    form_fields = [
        'multi_value_type',
        'text',
        'multi_cell_style',
        'sample_text',
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
        form.fields['sample_text'].help_text = 'Only used in setting the table up'
        form.fields['multi_cell_style'] = ModelChoiceField(
            queryset=MultiCellStyle.objects.filter(multi_value_report_id=self.object.report_id),
            widget=Select2(),
            required=False,
        )
        form.add_trigger(
            'multi_value_type',
            'onchange',
            [
                {
                    'selector': '#div_id_text',
                    'values': {
                        MultiValueReportCell.MultiValueType.STATIC_TEXT: 'show',
                        MultiValueReportCell.MultiValueType.EQUATION: 'show',
                    },
                    'default': 'hide',
                },
                {
                    'selector': '#div_id_sample_text',
                    'values': {
                        MultiValueReportCell.MultiValueType.STATIC_TEXT: 'hide',
                    },
                    'default': 'show',
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
            'sample_text',
            'multi_cell_style',
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


class MultiValueReportCellsModal(Modal):
    button_container_class = 'text-center'
    modal_title = 'Edit Cells'
    size = 'xl'

    @staticmethod
    def render_html(table_data, multi_value_report):
        html = ('<table class="table table-bordered kanban_summary">'
                '<tr><td></td>')
        for cols_index, cell in enumerate(table_data[0], start=1):
            letter = excel_column_name(cols_index)
            html += f'<td>{letter}</td>'
        html += '</tr>'
        for row_index, row in enumerate(table_data, start=1):
            html += f'<tr><td>{row_index}</td>'
            for cols_index, cell in enumerate(row, start=1):
                if cell is None:
                    link = show_modal(
                        'advanced_report_builder:multi_value_cell_modal',
                        '',
                        f'report_id-{multi_value_report.id}-row-{row_index}-column-{cols_index}',
                        href=True,
                        font_awesome='fas fa-edit',
                    )

                    html += f'<td><div class="d-flex align-items-center"><a href="{link}" class="ml-auto"><i class="fas fa-plus ml-auto"></i></a></div</td>'
                elif cell['value'] is not None:
                    attrs = []
                    multi_value_report_cell = cell['cell']
                    col_span = multi_value_report_cell.col_span
                    row_span = multi_value_report_cell.row_span
                    if col_span > 1:
                        attrs.append(f'colspan="{col_span}"')
                    if row_span > 1:
                        attrs.append(f'rowspan="{row_span}"')
                    value = cell['value']

                    link = show_modal(
                        'advanced_report_builder:multi_value_cell_modal',
                        '',
                        'pk-',
                        cell['cell'].id,
                        href=True,
                        font_awesome='fas fa-edit',
                    )
                    if multi_value_report_cell.multi_cell_style is not None:
                        attrs.append('style="' + multi_value_report_cell.multi_cell_style.get_td_style() + '"')
                        attrs.append('class="' + multi_value_report_cell.multi_cell_style.get_td_class() + '"')
                    attrs_html = ''
                    if len(attrs) > 0:
                        attrs_html = ' ' + ' '.join(attrs)

                    html += (
                        f'<td{attrs_html}><div class="d-flex align-items-center">'
                        f'{value}'
                        f'<a href="{link}" class="ml-auto"><i class="fas fa-edit"></i></a>'
                        f'</div></td>'
                    )
            html += '</tr>'

        html += '</table>'
        return html

    def get_table_data(self, multi_value_report):
        table_data = [[None for _ in range(multi_value_report.columns)] for _ in range(multi_value_report.rows)]
        multi_value_report_cells = MultiValueReportCell.objects.filter(report=multi_value_report).order_by(
            'row', 'column'
        )
        for multi_value_report_cell in multi_value_report_cells:
            row = multi_value_report_cell.row - 1
            column = multi_value_report_cell.column - 1
            if table_data[row][column] is not None:
                continue
            multi_value_type = multi_value_report_cell.multi_value_type
            if multi_value_type == MultiValueReportCell.MultiValueType.STATIC_TEXT:
                value = multi_value_report_cell.text
            elif multi_value_report_cell.sample_text:
                value = multi_value_report_cell.sample_text
            else:
                value = '123'

            table_data[row][column] = {'value': value, 'cell': multi_value_report_cell}

            if multi_value_report_cell.row_span > 1 or multi_value_report_cell.col_span > 1:
                for row_offset in range(multi_value_report_cell.row_span):
                    for col_offset in range(multi_value_report_cell.col_span):
                        # skip the main (top-left) cell
                        if row_offset == 0 and col_offset == 0:
                            continue
                        if (
                            len(table_data) > row + row_offset
                            and len(table_data[row + row_offset]) > column + col_offset
                        ):
                            table_data[row + row_offset][column + col_offset] = {'value': None}

        return table_data

    def modal_content(self):
        multi_value_report = MultiValueReport.objects.get(pk=self.slug['multi_value_report_id'])
        table_data = self.get_table_data(multi_value_report)

        return self.render_html(table_data=table_data, multi_value_report=multi_value_report)


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
        exp = ExpressionBuilder()
        multi_value_report_equations = []
        for multi_value_report_cell in multi_value_report_cells:
            cell_name = excel_column_name(multi_value_report_cell.column, row=multi_value_report_cell.row)
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
            elif multi_value_type == MultiValueReportCell.MultiValueType.AVERAGE_SUM_FROM_COUNT:
                self._process_aggregations(
                    field=multi_value_report_cell.field,
                    report_builder_class=report_builder_class,
                    base_model=base_model,
                    decimal_places=multi_value_report_cell.decimal_places,
                    fields=fields,
                    aggregations_type=ANNOTATION_CHOICE_AVERAGE_SUM_FROM_COUNT,
                )

            elif multi_value_type in [
                MultiValueReportCell.MultiValueType.AVERAGE_SUM_OVER_TIME,
                MultiValueReportCell.MultiValueType.AVERAGE_SUM_OVER_TIME_EXCLUDING_WEEKENDS,
            ]:
                exclude_weekdays = None
                if multi_value_type == MultiValueReportCell.MultiValueType.AVERAGE_SUM_OVER_TIME_EXCLUDING_WEEKENDS:
                    exclude_weekdays = [1, 7]

                divider = self.get_period_divider(
                    annotation_value_choice=multi_value_report_cell.average_scale,
                    start_date_type=multi_value_report_cell.average_start_period,
                    end_date_type=multi_value_report_cell.average_end_period,
                    exclude_weekdays=exclude_weekdays,
                )
                self._process_aggregations(
                    field=multi_value_report_cell.field,
                    report_builder_class=report_builder_class,
                    base_model=base_model,
                    decimal_places=multi_value_report_cell.decimal_places,
                    fields=fields,
                    aggregations_type=ANNOTATION_CHOICE_SUM,
                    divider=divider,
                )

            elif multi_value_type == MultiValueReportCell.MultiValueType.PERCENT:
                self._process_percentage(
                    denominator_field=multi_value_report_cell.field,
                    numerator_field=multi_value_report_cell.numerator,
                    report_builder_class=report_builder_class,
                    decimal_places=multi_value_report_cell.decimal_places,
                    base_model=base_model,
                    fields=fields,
                )
            elif multi_value_type == MultiValueReportCell.MultiValueType.PERCENT_FROM_COUNT:
                numerator_filter = self.process_filters(search_filter_data=multi_value_report_cell.extra_query)
                self._process_percentage_from_count(
                    numerator_filter=numerator_filter,
                    decimal_places=multi_value_report_cell.decimal_places,
                    fields=fields,
                )
            elif multi_value_type == MultiValueReportCell.MultiValueType.EQUATION:
                multi_value_report_equations.append((cell_name, multi_value_report_cell))

            if fields:
                value, raw_value = self.render_value(base_model=base_model, fields=fields)
                if raw_value is not None:
                    try:
                        raw_value = float(raw_value)
                    except ValueError:
                        pass
                    exp.add_to_global(name=cell_name, value=raw_value)

            table_data[row][column] = {'value': value, 'cell': multi_value_report_cell}

            if multi_value_report_cell.row_span > 1 or multi_value_report_cell.col_span > 1:
                for row_offset in range(multi_value_report_cell.row_span):
                    for col_offset in range(multi_value_report_cell.col_span):
                        # skip the main (top-left) cell
                        if row_offset == 0 and col_offset == 0:
                            continue

                        table_data[row + row_offset][column + col_offset] = {'value': None}

        unresolved = multi_value_report_equations[:]  # initial list
        previous_count = None

        while previous_count is None or len(unresolved) < previous_count:
            previous_count = len(unresolved)
            next_unresolved = []

            for cell_name, equation in unresolved:
                row = equation.row - 1
                column = equation.column - 1

                try:
                    value = exp.run_statement(equation.text)
                    exp.add_to_global(name=cell_name, value=value)
                except ExpressionVariableError as e:
                    # Could not evaluate yet — keep it for later
                    next_unresolved.append((cell_name, equation))
                    value = e.value

                table_data[row][column]['value'] = value

            unresolved = next_unresolved

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
                    attrs = []
                    multi_value_report_cell = cell['cell']
                    col_span = multi_value_report_cell.col_span
                    row_span = multi_value_report_cell.row_span
                    if col_span > 1:
                        attrs.append(f'colspan="{col_span}"')
                    if row_span > 1:
                        attrs.append(f'rowspan="{row_span}"')
                    value = cell['value']

                    if multi_value_report_cell.multi_cell_style is not None:
                        attrs.append('style="' + multi_value_report_cell.multi_cell_style.get_td_style() + '"')
                        attrs.append('class="' + multi_value_report_cell.multi_cell_style.get_td_class() + '"')
                    attrs_html = ''
                    if len(attrs) > 0:
                        attrs_html = ' ' + ' '.join(attrs)

                    html += f'<td{attrs_html}>{value}</td>'
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
        if len(table.raw_data) > 0 and len(table.raw_data[0]) > 0:
            return value, table.raw_data[0][0]
        return value, None
