import contextlib
import json
import logging
import re
from copy import deepcopy
from datetime import datetime, timedelta

from crispy_forms.layout import HTML
from django.conf import settings
from django.core.exceptions import FieldDoesNotExist, FieldError
from django.forms import CharField, ChoiceField, ModelChoiceField
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.html import escape
from django_datatables.columns import ColumnBase, MenuColumn
from django_datatables.datatables import DatatableTable
from django_datatables.helpers import DUMMY_ID
from django_datatables.widgets import DataTableWidget
from django_menus.menu import HtmlMenu, MenuItem
from django_modals.fields import FieldEx
from django_modals.form_helpers import HorizontalNoEnterHelper
from django_modals.forms import CrispyForm
from django_modals.helper import show_modal
from django_modals.modals import FormModal, Modal, ModelFormModal
from django_modals.processes import PERMISSION_OFF, PROCESS_EDIT_DELETE
from django_modals.widgets.select2 import Select2, Select2Multiple
from django_modals.widgets.widgets import Toggle
from expression_builder.exceptions import ExpressionVariableError
from expression_builder.expression_builder import ExpressionBuilder

from advanced_report_builder.column_types import DATE_FIELDS
from advanced_report_builder.columns import ReportBuilderNumberColumn
from advanced_report_builder.exceptions import ReportError
from advanced_report_builder.globals import (
    ANNOTATION_CHOICE_AVERAGE_SUM_FROM_COUNT,
    ANNOTATION_CHOICE_SUM,
    ANNOTATION_VALUE_DAY,
    ANNOTATION_VALUE_FUNCTIONS,
    ANNOTATION_VALUE_MONTH,
    ANNOTATION_VALUE_QUARTER,
    ANNOTATION_VALUE_YEAR,
    PREFIX_TYPE_CUSTOM,
)
from advanced_report_builder.models import (
    MultiCellStyle,
    MultiValueHeldQuery,
    MultiValueReport,
    MultiValueReportCell,
    MultiValueReportColumn,
    MultiValueReportRow,
    ReportType,
)
from advanced_report_builder.record_nav import RecordNavPlugin
from advanced_report_builder.toggle import RBToggle
from advanced_report_builder.utils import crispy_modal_link_args, excel_column_name, get_report_builder_class
from advanced_report_builder.variable_date import VariableDate
from advanced_report_builder.views.charts_base import ChartJSTable
from advanced_report_builder.views.datatables.modal import TableFieldForm, TableFieldModal
from advanced_report_builder.views.datatables.utils import TableUtilsMixin
from advanced_report_builder.views.helpers import QueryBuilderModelForm
from advanced_report_builder.views.modals_base import QueryBuilderModalBase
from advanced_report_builder.views.query_modal.mixin import MultiQueryModalMixin
from advanced_report_builder.views.value_base import ValueBaseView
from advanced_report_builder.widgets import SmallNumberInputWidget

logger = logging.getLogger(__name__)

# Data-merge variables available in a dynamic row's cell text, using ARB's ``{{ }}`` merge syntax:
# ``{{ value }}`` -> the row's group value (universal); for a date group field also ``{{ period }}``
# (period start / row label) and ``{{ period_end }}`` (the period's last day).
_PERIOD_MERGE_RE = re.compile(r'{{\s*(period_end|period|value)\s*}}')


def apply_dynamic_merge(text, spec, label_format):
    """Resolve the ``{{ value }}`` / ``{{ period }}`` / ``{{ period_end }}`` merge variables in a
    dynamic row's text. ``spec`` is one row descriptor from ``_distinct_row_specs``: a period spec
    (``spec['period'] == (start, end)``) or a value spec (``spec['value']``). Dates are formatted with
    the row's ``label_format``. Other ``{{ ... }}`` fields are left untouched.
    """
    if not text:
        return text
    if spec['period'] is not None:
        start, end = spec['period']
        value = period = start.strftime(label_format)
        period_end = (end - timedelta(days=1)).strftime(label_format)
    else:
        value = period = period_end = '' if spec['value'] is None else str(spec['value'])

    replacements = {'value': value, 'period': period, 'period_end': period_end}
    return _PERIOD_MERGE_RE.sub(lambda match: replacements[match.group(1)], text)


def _period_rule(field, start, end):
    """A query-builder AND group limiting ``field`` to [start, end)."""
    return {
        'condition': 'AND',
        'valid': True,
        'rules': [
            {
                'id': field,
                'field': field,
                'type': 'date',
                'operator': 'greater_or_equal',
                'value': start.strftime('%Y-%m-%d'),
            },
            {'id': field, 'field': field, 'type': 'date', 'operator': 'less', 'value': end.strftime('%Y-%m-%d')},
        ],
    }


def _and_period_filter(query_data, field, start, end):
    """AND a ``field in [start, end)`` restriction onto ``query_data`` (which may be empty), keeping
    any existing rules intact by nesting them alongside the period group under a top-level AND."""
    return _and_rules(query_data, _period_rule(field, start, end))


def _and_value_filter(query_data, field, value):
    """AND a ``field == value`` restriction onto ``query_data`` (used for value-grouped rows)."""
    rule = {
        'condition': 'AND',
        'valid': True,
        'rules': [{'id': field, 'field': field, 'type': 'string', 'operator': 'equal', 'value': value}],
    }
    return _and_rules(query_data, rule)


def _and_rules(query_data, extra_group):
    """AND ``extra_group`` onto ``query_data`` (which may be empty), nesting any existing rules
    alongside it under a top-level AND so their own condition is preserved."""
    if not query_data or not query_data.get('rules'):
        return extra_group
    return {'condition': 'AND', 'valid': True, 'rules': [deepcopy(query_data), extra_group]}


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

            query_menu_items = [
                MenuItem(
                    f'advanced_report_builder:multi_value_query_modal,pk-{DUMMY_ID}',
                    menu_display='Edit',
                    css_classes='btn btn-sm btn-outline-dark',
                    font_awesome='fas fa-pencil',
                ),
            ]

            form.fields['held_queries'] = CharField(
                required=False,
                label='Held Queries',
                widget=DataTableWidget(
                    model=MultiValueHeldQuery,
                    fields=[
                        '_.index',
                        '.id',
                        ColumnBase(column_name='held_report_name', field='name', title='Name'),
                        ColumnBase(
                            column_name='held_report_report_name', field='report_type__name', title='Report Type'
                        ),
                        MenuColumn(
                            column_name='menu',
                            field='id',
                            column_defs={'orderable': False, 'className': 'dt-right'},
                            menu=HtmlMenu(self.request, 'button_group').add_items(*query_menu_items),
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
                    'advanced_report_builder:multi_value_query_modal',
                    'Add Held Query',
                    'multi_value_report_id-',
                    self.object.id,
                    div=True,
                    div_classes='form-buttons',
                    button_classes='btn btn-primary',
                    font_awesome='fa fa-plus',
                ),
                'held_queries',
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

    def form_valid(self, form):
        org_id = self.object.pk if hasattr(self, 'object') else None
        created = org_id is None
        instance = form.save(commit=False)
        instance._current_user = self.request.user
        instance.save()

        if created:
            self.modal_redirect(
                self.request.resolver_match.view_name,
                slug=f'pk-{self.object.id}-new-True',
            )
        else:
            url_name = getattr(settings, 'REPORT_BUILDER_DETAIL_URL_NAME', '')
            if url_name and self.slug.get('new'):
                url = reverse(url_name, kwargs={'slug': self.object.slug})
                self.add_command('redirect', url=url)
        if not self.response_commands:
            self.add_command('reload')

        return self.command_response()


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

    form_fields = ['name', 'align_type', 'bold', 'italic', 'font_size', 'font_colour', 'background_colour']


class MultiValueReportColumnModal(ModelFormModal):
    process = PROCESS_EDIT_DELETE
    permission_delete = PERMISSION_OFF
    model = MultiValueReportColumn

    widgets = {
        'width': SmallNumberInputWidget,
        'width_type': Select2,
    }

    form_fields = ['width', 'width_type']


class MultiValueHeldQueryForm(QueryBuilderModelForm):
    cancel_class = 'btn-secondary modal-cancel'

    class Meta:
        model = MultiValueHeldQuery
        fields = ['name', 'query', 'report_type']


class MultiValueHeldQueryModal(QueryBuilderModalBase):
    process = PROCESS_EDIT_DELETE
    permission_delete = PERMISSION_OFF
    form_class = MultiValueHeldQueryForm
    template_name = 'advanced_report_builder/multi_values/held_modal.html'

    def form_setup(self, form, *_args, **_kwargs):
        fields = [
            'name',
            'report_type',
            FieldEx('query', template='advanced_report_builder/query_builder.html'),
        ]
        return fields

    def form_valid(self, form):
        form.save()
        return self.command_response('reload')


class MultiValueReportRowForm(QueryBuilderModelForm):
    """Config for a dynamic grid row (from the "Dynamic" button on the cells grid): the field to
    group rows by (a date -> one row per period; any other field -> one row per distinct value),
    plus an optional base filter. ``report_type`` and ``base_query`` are named to drive the stock
    query-builder JS."""

    cancel_class = 'btn-secondary modal-cancel'

    class Meta:
        model = MultiValueReportRow
        fields = [
            'report_type',
            'group_field',
            'period',
            'base_query',
            'label_format',
            'limit',
            'descending',
            'show_blank_dates',
        ]
        widgets = {
            'report_type': Select2,
            'period': Select2,
            'limit': SmallNumberInputWidget,
            'descending': RBToggle,
            'show_blank_dates': RBToggle,
        }


class MultiValueReportRowModal(QueryBuilderModalBase):
    process = PROCESS_EDIT_DELETE
    permission_delete = PERMISSION_OFF
    model = MultiValueReportRow
    form_class = MultiValueReportRowForm
    template_name = 'advanced_report_builder/multi_values/row_modal.html'
    helptext = {
        'group_field': (
            'Field to group the rows by. A date field gives one row per period (set Period); any '
            'other field (user, type, ...) gives one row per distinct value.'
        ),
        'period': 'Row per this period - only used when Group field is a date.',
        'label_format': 'Python strftime for date labels, e.g. %d/%m/%Y (dates only).',
        'show_blank_dates': 'Date grouping only: also show periods with no data (blank rows).',
    }

    def form_setup(self, form, *_args, **_kwargs):
        for field_name, text in self.helptext.items():
            if field_name in form.fields:
                form.fields[field_name].help_text = text

        # group_field is a Select2 of the report type's fields (populated by report_type), rather than
        # free text. On a report_type change the modal reposts with `data`; otherwise use the instance.
        if 'data' in _kwargs and len(_kwargs['data']) > 0:
            group_field = _kwargs['data'].get('group_field')
            report_type_id = _kwargs['data'].get('report_type')
            report_type = get_object_or_404(ReportType, id=report_type_id) if report_type_id else None
        else:
            group_field = form.instance.group_field
            report_type = form.instance.report_type

        self.setup_field(
            field_type='all',
            form=form,
            field_name='group_field',
            selected_field_id=group_field,
            report_type=report_type,
        )
        return [
            'report_type',
            'group_field',
            'period',
            FieldEx('base_query', template='advanced_report_builder/query_builder.html'),
            'label_format',
            'limit',
            'descending',
            'show_blank_dates',
        ]

    def select2_group_field(self, **kwargs):
        return self.get_fields_for_select2(
            field_type='all', report_type=kwargs['report_type'], search_string=kwargs.get('search')
        )

    def form_valid(self, form):
        instance = form.save(commit=False)
        # Created via the cells grid button, which passes the report id + row number in the slug.
        if not instance.multi_value_report_id:
            instance.multi_value_report_id = self.slug['multi_value_report_id']
            instance.row = int(self.slug['row'])
        instance.save()
        return self.command_response('reload')


class MultiValueReportCellForm(QueryBuilderModelForm):
    cancel_class = 'btn-secondary modal-cancel'

    class Meta:
        model = MultiValueReportCell
        fields = [
            'multi_value_type',
            'text',
            'multi_cell_style',
            'label',
            'row',
            'column',
            'col_span',
            'row_span',
            'report_type',
            'field',
            'numerator',
            'group_field',
            'prefix_type',
            'prefix',
            'decimal_places',
            'multi_value_held_query',
            'show_breakdown',
            'breakdown_fields',
            'record_nav',
            'average_scale',
            'average_start_period',
            'average_end_period',
            'query_data',
            'extra_query_data',
        ]
        widgets = {
            'report_tags': Select2Multiple,
            'show_breakdown': Toggle(attrs={'data-onstyle': 'success', 'data-on': 'YES', 'data-off': 'NO'}),
            'record_nav': Toggle(attrs={'data-onstyle': 'success', 'data-on': 'YES', 'data-off': 'NO'}),
            'row': SmallNumberInputWidget,
            'column': SmallNumberInputWidget,
            'col_span': SmallNumberInputWidget,
            'row_span': SmallNumberInputWidget,
            'decimal_places': SmallNumberInputWidget,
        }


class MultiValueReportCellModal(MultiQueryModalMixin, QueryBuilderModalBase):
    template_name = 'advanced_report_builder/multi_values/modal.html'
    size = 'xl'
    process = PROCESS_EDIT_DELETE
    permission_delete = PERMISSION_OFF
    model = MultiValueReportCell
    helper_class = HorizontalNoEnterHelper
    form_class = MultiValueReportCellForm

    @property
    def modal_title(self):
        if self.object.row and self.object.column:
            title = excel_column_name(int(self.object.column), row=int(self.object.row))
        else:
            title = ' value'

        return [f'Add {title}', f'Edit {title}']

    def form_setup(self, form, *_args, **_kwargs):
        if not form.instance.pk:
            form.fields['record_nav'].initial = getattr(settings, 'REPORT_BUILDER_RECORD_NAV_DEFAULT', True)

        form.fields['label'].help_text = 'Used when setting up the table and for the show breakdown title.'
        form.fields['multi_cell_style'] = ModelChoiceField(
            queryset=MultiCellStyle.objects.filter(multi_value_report_id=self.object.multi_value_report_id),
            widget=Select2(),
            required=False,
        )

        form.fields['extra_query_data'].label = 'Numerator'

        # When this cell is on a dynamic (repeat) row, offer buttons to insert the period merge
        # variables into the Static Text field, so the {{ }} syntax needn't be typed.
        report_id = self.object.multi_value_report_id or self.slug.get('multi_value_report_id')
        row_number = self.object.row or self.slug.get('row')
        self.is_dynamic_row = bool(
            report_id
            and row_number
            and MultiValueReportRow.objects.filter(multi_value_report_id=report_id, row=row_number).exists()
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
                    'selector': '#div_id_period_insert',
                    'values': {
                        MultiValueReportCell.MultiValueType.STATIC_TEXT: 'show',
                        MultiValueReportCell.MultiValueType.EQUATION: 'show',
                    },
                    'default': 'hide',
                },
                {
                    'selector': '#div_id_label_text',
                    'values': {
                        MultiValueReportCell.MultiValueType.STATIC_TEXT: 'hide',
                    },
                    'default': 'show',
                },
                {
                    'selector': '#div_id_field',
                    'values': {
                        MultiValueReportCell.MultiValueType.STATIC_TEXT: 'hide',
                        MultiValueReportCell.MultiValueType.EQUATION: 'hide',
                        MultiValueReportCell.MultiValueType.COUNT: 'hide',
                        MultiValueReportCell.MultiValueType.PERCENT_FROM_COUNT: 'hide',
                    },
                    'default': 'show',
                },
                {
                    'selector': '#div_id_prefix_type',
                    'values': {
                        MultiValueReportCell.MultiValueType.STATIC_TEXT: 'hide',
                        MultiValueReportCell.MultiValueType.EQUATION: 'hide',
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
                        MultiValueReportCell.MultiValueType.EQUATION: 'hide',
                    },
                    'default': 'show',
                },
                {
                    'selector': '#div_id_decimal_places',
                    'values': {
                        MultiValueReportCell.MultiValueType.STATIC_TEXT: 'hide',
                        MultiValueReportCell.MultiValueType.EQUATION: 'hide',
                    },
                    'default': 'show',
                },
                {
                    'selector': '#div_id_group_field',
                    'values': {
                        MultiValueReportCell.MultiValueType.STATIC_TEXT: 'hide',
                        MultiValueReportCell.MultiValueType.EQUATION: 'hide',
                    },
                    'default': 'show',
                },
                {
                    'selector': '#div_id_show_breakdown',
                    'values': {
                        MultiValueReportCell.MultiValueType.STATIC_TEXT: 'hide',
                        MultiValueReportCell.MultiValueType.EQUATION: 'hide',
                    },
                    'default': 'show',
                },
                {
                    'selector': '#div_id_query_data',
                    'values': {
                        MultiValueReportCell.MultiValueType.STATIC_TEXT: 'hide',
                        MultiValueReportCell.MultiValueType.EQUATION: 'hide',
                    },
                    'default': 'show',
                },
                {
                    'selector': '#div_id_extra_query_data',
                    'values': {
                        MultiValueReportCell.MultiValueType.PERCENT: 'show',
                    },
                    'default': 'hide',
                },
                {
                    'selector': '#div_id_multi_value_held_query',
                    'values': {
                        MultiValueReportCell.MultiValueType.STATIC_TEXT: 'hide',
                        MultiValueReportCell.MultiValueType.EQUATION: 'hide',
                    },
                    'default': 'show',
                },
            ],
        )

        form.add_trigger(
            'prefix_type',
            'onchange',
            [
                {
                    'selector': '#div_id_prefix',
                    'values': {PREFIX_TYPE_CUSTOM: 'show'},
                    'default': 'hide',
                }
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
                {
                    'selector': '#div_id_record_nav',
                    'values': {'checked': 'show'},
                    'default': 'hide',
                },
            ],
        )
        if 'data' in _kwargs and len(_kwargs['data']) > 0:
            field = _kwargs['data'].get('field')
            numerator = _kwargs['data'].get('numerator')
            group_field = _kwargs['data'].get('group_field')
            report_type_id = _kwargs['data'].get('report_type')
            if report_type_id != '':
                report_type = get_object_or_404(ReportType, id=report_type_id)
            else:
                report_type = form.instance.report_type
        else:
            field = form.instance.field
            report_type = form.instance.report_type
            numerator = form.instance.numerator
            group_field = form.instance.group_field

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

        self.setup_field(
            field_type='all',
            form=form,
            field_name='group_field',
            selected_field_id=group_field,
            report_type=report_type,
        )
        form.fields['group_field'].help_text = (
            "On a dynamic row, limits this cell to the row's value using this field. Leave blank to "
            "use the dynamic row's own group field when this cell has the same report type."
        )
        form.fields['text'].help_text = (
            'On a dynamic row, use {{ value }} to show the row value (or {{ period }} / {{ period_end }} '
            'for date grouping).'
        )

        url = reverse(
            'advanced_report_builder:multi_value_field_modal',
            kwargs={'slug': 'selector-99999-data-FIELD_INFO-report_type_id-REPORT_TYPE_ID'},
        )

        range_type_choices = VariableDate.RANGE_TYPE_CHOICES
        form.fields['average_start_period'] = ChoiceField(required=False, choices=range_type_choices)
        form.fields['average_end_period'] = ChoiceField(required=False, choices=range_type_choices)

        form.fields['multi_value_held_query'].widget = Select2(attrs={'ajax': True})

        if self.object.multi_value_held_query is not None:
            selected_data = [
                {'id': self.object.multi_value_held_query_id, 'text': self.object.multi_value_held_query.name}
            ]
            form.fields['multi_value_held_query'].widget.select_data = selected_data

        # crispy HTML() renders its content as a Django template, so wrap the literal {{ }} tokens
        # shown on the buttons in {% verbatim %} so they aren't evaluated.
        period_insert = HTML(
            '<div id="div_id_period_insert" class="form-group row">'
            '<div class="col-3"></div><div class="col-9">'
            '<button type="button" class="btn btn-sm btn-outline-secondary mr-1" '
            'onclick="mv_insert_period_token(\'value\')">'
            'Insert {% verbatim %}{{ value }}{% endverbatim %}</button>'
            '<button type="button" class="btn btn-sm btn-outline-secondary mr-1" '
            'onclick="mv_insert_period_token(\'period\')">'
            'Insert {% verbatim %}{{ period }}{% endverbatim %}</button>'
            '<button type="button" class="btn btn-sm btn-outline-secondary" '
            'onclick="mv_insert_period_token(\'period_end\')">'
            'Insert {% verbatim %}{{ period_end }}{% endverbatim %}</button>'
            '</div></div>'
        )

        fields = [
            'multi_value_type',
            'text',
            *([period_insert] if self.is_dynamic_row else []),
            'label',
            'multi_cell_style',
            'row',
            'column',
            'col_span',
            'row_span',
            'report_type',
            'field',
            'numerator',
            'group_field',
            'prefix_type',
            'prefix',
            'decimal_places',
            'multi_value_held_query',
            'show_breakdown',
            'average_scale',
            'average_start_period',
            'average_end_period',
            FieldEx(
                'breakdown_fields',
                template='advanced_report_builder/select_column.html',
                extra_context={'select_column_url': url, 'command_prefix': ''},
            ),
            FieldEx(
                'record_nav',
                template='django_modals/fields/label_checkbox.html',
            ),
            FieldEx('query_data', template='advanced_report_builder/query_builder.html'),
            FieldEx('extra_query_data', template='advanced_report_builder/query_builder.html'),
        ]
        return fields

    def select2_group_field(self, **kwargs):
        return self.get_fields_for_select2(
            field_type='all', report_type=kwargs['report_type'], search_string=kwargs.get('search')
        )

    def select2_multi_value_held_query(self, **kwargs):
        results = []
        if kwargs.get('report_type') != '':
            multi_value_held_queries = MultiValueHeldQuery.objects.filter(
                report_type_id=kwargs['report_type'], multi_value_report=self.object.multi_value_report
            )
            search = kwargs.get('search', '')
            if search != '':
                multi_value_held_queries = multi_value_held_queries.filter(name__icontains=search)
            for multi_value_held_query in multi_value_held_queries:
                results.append({'id': multi_value_held_query.id, 'text': multi_value_held_query.name})

        return JsonResponse({'results': results})

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
        dynamic_rows = {row.row: row for row in multi_value_report.multivaluereportrow_set.all()}
        html = '<table class="table table-bordered kanban_summary"><tr><td></td>'
        columns_data = {}
        for multi_value_report_column in multi_value_report.multivaluereportcolumn_set.all():
            columns_data[multi_value_report_column.column] = multi_value_report_column

        for cols_index, cell in enumerate(table_data[0], start=1):
            letter = excel_column_name(cols_index)
            if cols_index in columns_data:
                multi_value_report_column = columns_data[cols_index]
                link = show_modal(
                    'advanced_report_builder:multi_value_column_modal',
                    '',
                    f'pk-{multi_value_report_column.id}',
                    href=True,
                )
                style = multi_value_report_column.get_td_style()
                html += (
                    f'<td style="{style}"><div class="d-flex align-items-center">{letter}'
                    f'<a href="{link}" class="ml-auto"><i class="fas fa-edit ml-auto"></i></a></div></td>'
                )
            else:
                link = show_modal(
                    'advanced_report_builder:multi_value_column_modal',
                    '',
                    f'multi_value_report_id-{multi_value_report.id}-column-{cols_index}',
                    href=True,
                )
                html += (
                    f'<td><div class="d-flex align-items-center">{letter}'
                    f'<a href="{link}" class="ml-auto"><i class="fas fa-plus ml-auto"></i></a></div></td>'
                )
        html += '</tr>'
        for row_index, row in enumerate(table_data, start=1):
            dynamic_row = dynamic_rows.get(row_index)
            if dynamic_row is not None:
                row_link = show_modal(
                    'advanced_report_builder:multi_value_row_modal', '', f'pk-{dynamic_row.id}', href=True
                )
                row_button = (
                    f'<a href="{row_link}" class="btn btn-warning btn-sm mt-1" title="Dynamic row - edit">'
                    f'<i class="fas fa-bolt"></i></a>'
                )
            else:
                row_link = show_modal(
                    'advanced_report_builder:multi_value_row_modal',
                    '',
                    f'multi_value_report_id-{multi_value_report.id}-row-{row_index}',
                    href=True,
                )
                row_button = (
                    f'<a href="{row_link}" class="btn btn-outline-secondary btn-sm mt-1" title="Make row dynamic">'
                    f'<i class="fas fa-bolt"></i></a>'
                )
            html += f'<tr><td>{row_index}<br>{row_button}</td>'
            for cols_index, cell in enumerate(row, start=1):
                if cell is None:
                    add_link = show_modal(
                        'advanced_report_builder:multi_value_cell_modal',
                        '',
                        f'multi_value_report_id-{multi_value_report.id}-row-{row_index}-column-{cols_index}',
                        href=True,
                    )
                    copy_from_link = show_modal(
                        'advanced_report_builder:multi_value_cell_copy_from_modal',
                        '',
                        f'pk-{multi_value_report.id}-row-{row_index}-column-{cols_index}',
                        href=True,
                    )

                    html += f'''
                            <td>
                              <div class="d-flex align-items-center">
                                <div class="ml-auto btn-group" role="group">
                                  <a href="{add_link}" class="btn btn-outline-primary btn-sm">
                                    <i class="fas fa-plus"></i>
                                  </a>
                                  <a href="{copy_from_link}" class="btn btn-outline-secondary btn-sm">
                                    <i class="fas fa-file-import"></i>
                                  </a>
                                </div>
                              </div>
                            </td>
                            '''
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
                    )
                    if multi_value_report_cell.multi_cell_style is not None:
                        attrs.append('style="' + multi_value_report_cell.multi_cell_style.get_td_style() + '"')
                        attrs.append('class="' + multi_value_report_cell.multi_cell_style.get_td_class() + '"')
                    attrs_html = ''
                    if len(attrs) > 0:
                        attrs_html = ' ' + ' '.join(attrs)

                    html += f'''
                        <td{attrs_html}>
                          <div class="d-flex align-items-center">
                            {value}
                            <div class="ml-auto btn-group" role="group">
                              <a href="{link}" class="btn btn-outline-primary btn-sm">
                                <i class="fas fa-edit"></i>
                              </a>
                            </div>
                          </div>
                        </td>
                        '''
            html += '</tr>'

        html += '</table>'
        return html

    def get_table_data(self, multi_value_report):
        table_data = [[None for _ in range(multi_value_report.columns)] for _ in range(multi_value_report.rows)]
        multi_value_report_cells = MultiValueReportCell.objects.filter(
            multi_value_report=multi_value_report,
            row__lte=multi_value_report.rows,
            column__lte=multi_value_report.columns,
        ).order_by('row', 'column')
        for multi_value_report_cell in multi_value_report_cells:
            row = multi_value_report_cell.row - 1
            column = multi_value_report_cell.column - 1
            if table_data[row][column] is not None:
                continue
            multi_value_type = multi_value_report_cell.multi_value_type
            if multi_value_type == MultiValueReportCell.MultiValueType.STATIC_TEXT:
                value = multi_value_report_cell.text
            elif multi_value_report_cell.label:
                value = multi_value_report_cell.label
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

    def __init__(self, *args, **kwargs):
        self.current_multi_value_report_cell = None
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
            *self.queries_option_menus(report=self.report, dashboard_report=self.dashboard_report),
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
        return self.edit_report_menu(request=self.request, chart_report_id=self.chart_report.id)

    def edit_report_menu(self, request, chart_report_id, slug_str=None):
        return [
            MenuItem(
                f'advanced_report_builder:multi_value_modal,pk-{chart_report_id}',
                menu_display='Edit',
                font_awesome='fas fa-pencil-alt',
                css_classes=['btn-primary'],
            ),
            *self.duplicate_menu(request=request, report_id=chart_report_id),
        ]

    @staticmethod
    def _cell_error(cell_name, err):
        """Contain a per-cell failure: log the full exception server-side and return a short,
        HTML-escaped message for display. The cell value is later emitted into ``{{ html|safe }}``,
        so the returned text MUST be escaped to avoid injecting an exception message into the page."""
        message = getattr(err, 'value', err)
        logger.warning('MultiValueReport cell %s failed to render: %s', cell_name, message, exc_info=err)
        return escape(f'{cell_name}: {message}')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs) if hasattr(super(), 'get_context_data') else {}

        dynamic_rows = {row.row: row for row in self.chart_report.multivaluereportrow_set.all()}
        if dynamic_rows:
            context['html'] = self.render_html(table_data=self._get_dynamic_table_data(dynamic_rows))
            return context

        multi_value_report_cells = (
            MultiValueReportCell.objects.filter(
                multi_value_report=self.chart_report,
                row__lte=self.chart_report.rows,
                column__lte=self.chart_report.columns,
            )
            .select_related('multi_value_held_query')
            .order_by('row', 'column')
        )

        table_data = [[None for _ in range(self.chart_report.columns)] for _ in range(self.chart_report.rows)]
        exp = ExpressionBuilder()
        multi_value_report_equations = []
        for multi_value_report_cell in multi_value_report_cells:
            cell_name = excel_column_name(multi_value_report_cell.column, row=multi_value_report_cell.row)

            row = multi_value_report_cell.row - 1
            column = multi_value_report_cell.column - 1
            if table_data[row][column] is not None:
                continue

            if multi_value_report_cell.multi_value_type == MultiValueReportCell.MultiValueType.EQUATION:
                multi_value_report_equations.append((cell_name, multi_value_report_cell))
                value, append_str = '', ''
            else:
                value, append_str = self._evaluate_cell(
                    multi_value_report_cell=multi_value_report_cell, cell_name=cell_name, exp=exp
                )

            table_data[row][column] = {'value': value, 'cell': multi_value_report_cell, 'append_str': append_str}

            if multi_value_report_cell.row_span > 1 or multi_value_report_cell.col_span > 1:
                for row_offset in range(multi_value_report_cell.row_span):
                    for col_offset in range(multi_value_report_cell.col_span):
                        # skip the main (top-left) cell
                        if row_offset == 0 and col_offset == 0:
                            continue

                        table_data[row + row_offset][column + col_offset] = {'value': None}

        self._resolve_equations(table_data=table_data, equations=multi_value_report_equations, exp=exp)

        context['html'] = self.render_html(table_data=table_data)
        return context

    def _evaluate_cell(self, multi_value_report_cell, cell_name, exp):
        """Compute a single (non-equation) cell's display value and trailing symbol.

        Extracted so the fixed grid and the dynamic-row grid share identical cell semantics. Feeds
        the cell's numeric result into the expression builder so equation cells can reference it.
        """
        base_model = multi_value_report_cell.get_base_model()
        value = ''
        append_str = ''
        report_builder_class = None
        multi_value_type = multi_value_report_cell.multi_value_type
        if base_model is not None:
            report_builder_class = get_report_builder_class(
                model=base_model, report_type=multi_value_report_cell.report_type
            )

        fields = []
        try:
            if multi_value_type == MultiValueReportCell.MultiValueType.STATIC_TEXT:
                value = multi_value_report_cell.text
            elif multi_value_type == MultiValueReportCell.MultiValueType.COUNT:
                self._get_count(fields=fields)
            elif multi_value_type == MultiValueReportCell.MultiValueType.SUM:
                if multi_value_report_cell.field is None:
                    value = 'Error no field selected'
                else:
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
                numerator_filter = self.process_filters(search_filter_data=multi_value_report_cell.extra_query_data)
                denominator_filter = self.process_filters(
                    search_filter_data=multi_value_report_cell.denominator_query_data
                )
                self._process_percentage(
                    numerator_filter=numerator_filter,
                    denominator_field=multi_value_report_cell.field,
                    numerator_field=multi_value_report_cell.numerator,
                    report_builder_class=report_builder_class,
                    decimal_places=multi_value_report_cell.decimal_places,
                    base_model=base_model,
                    fields=fields,
                    denominator_filter=denominator_filter,
                )
                append_str = '%'
            elif multi_value_type == MultiValueReportCell.MultiValueType.PERCENT_FROM_COUNT:
                numerator_filter = self.process_filters(search_filter_data=multi_value_report_cell.extra_query_data)
                self._process_percentage_from_count(
                    numerator_filter=numerator_filter,
                    decimal_places=multi_value_report_cell.decimal_places,
                    fields=fields,
                )
                append_str = '%'
        except ReportError as e:
            value = self._cell_error(cell_name, e)
        except Exception as e:  # noqa: BLE001 - contain a bad cell rather than 500-ing the whole grid
            value = self._cell_error(cell_name, e)

        if fields:
            try:
                value, raw_value = self.render_value(
                    base_model=base_model, fields=fields, multi_value_report_cell=multi_value_report_cell
                )
            # A cell that fails to render (e.g. a non-aggregatable field wrongly summed) must not
            # take down the whole report - show the error in the cell, prefixed with its grid
            # reference (e.g. "B2") so it is clear which cell failed.
            except Exception as e:  # noqa: BLE001
                value = self._cell_error(cell_name, e)
                raw_value = None
            if raw_value is not None:
                with contextlib.suppress(ValueError):
                    raw_value = float(raw_value)
                exp.add_to_global(name=cell_name, value=raw_value)
        elif value is not None:
            expression_value = value
            with contextlib.suppress(ValueError):
                expression_value = float(expression_value)
            exp.add_to_global(name=cell_name, value=expression_value)

        return value, append_str

    @staticmethod
    def _resolve_equations(table_data, equations, exp):
        unresolved = equations[:]  # initial list
        previous_count = None
        max_iterations = max(100, len(equations) * 2)
        iteration = 0

        while (previous_count is None or len(unresolved) < previous_count) and iteration < max_iterations:
            previous_count = len(unresolved)
            iteration += 1
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

    # --- Dynamic rows -----------------------------------------------------------------------------
    def _get_dynamic_table_data(self, dynamic_rows):
        """Build the grid when one or more rows are dynamic. Rows render top to bottom: a static row
        renders once; a dynamic row (one with a MultiValueReportRow config, keyed by row number in
        ``dynamic_rows``) is the template for one generated row per group value (a period for a date
        group field, else each distinct value), each cell limited to that value and Static Text able
        to show it via the ``{{ value }}`` / ``{{ period }}`` merge variables."""
        report = self.chart_report
        columns = report.columns
        cells = (
            MultiValueReportCell.objects.filter(multi_value_report=report, row__lte=report.rows, column__lte=columns)
            .select_related('multi_value_held_query')
            .order_by('row', 'column')
        )
        cells_by_row = {}
        for cell in cells:
            cells_by_row.setdefault(cell.row, []).append(cell)

        exp = ExpressionBuilder()
        table_data = []
        for row_number in range(1, report.rows + 1):
            row_cells = cells_by_row.get(row_number, [])
            row_config = dynamic_rows.get(row_number)
            if row_config is None:
                table_data.append(self._render_static_row(row_cells=row_cells, columns=columns, exp=exp))
            else:
                for spec in self._distinct_row_specs(row_config):
                    table_data.append(
                        self._render_dynamic_row(row_cells=row_cells, columns=columns, spec=spec, row_config=row_config)
                    )
        return table_data

    def _render_static_row(self, row_cells, columns, exp):
        data_row = [None for _ in range(columns)]
        for cell in row_cells:
            column = cell.column - 1
            if column >= columns or data_row[column] is not None:
                continue
            cell_name = excel_column_name(cell.column, row=cell.row)
            if cell.multi_value_type == MultiValueReportCell.MultiValueType.EQUATION:
                value, append_str = cell.text or '', ''
            else:
                value, append_str = self._evaluate_cell(multi_value_report_cell=cell, cell_name=cell_name, exp=exp)
            data_row[column] = {'value': value, 'cell': cell, 'append_str': append_str}
            for col_offset in range(1, cell.col_span):
                if column + col_offset < columns:
                    data_row[column + col_offset] = {'value': None}
        return data_row

    def _render_dynamic_row(self, row_cells, columns, spec, row_config):
        data_row = [None for _ in range(columns)]
        for cell in row_cells:
            column = cell.column - 1
            if column >= columns or data_row[column] is not None:
                continue
            cell_name = excel_column_name(cell.column, row=cell.row)
            dynamic_cell = self._dynamic_cell(template_cell=cell, spec=spec, row_config=row_config)
            if dynamic_cell.multi_value_type == MultiValueReportCell.MultiValueType.EQUATION:
                # Cross-row equations don't have a well-defined meaning in a dynamic grid yet.
                value, append_str = dynamic_cell.text or '', ''
            else:
                value, append_str = self._evaluate_cell(
                    multi_value_report_cell=dynamic_cell, cell_name=cell_name, exp=ExpressionBuilder()
                )
            data_row[column] = {'value': value, 'cell': dynamic_cell, 'append_str': append_str, 'spec': spec}
            for col_offset in range(1, cell.col_span):
                if column + col_offset < columns:
                    data_row[column + col_offset] = {'value': None}
        return data_row

    def _group_field_is_date(self, row_config):
        model = row_config.report_type.content_type.model_class()
        report_builder_class = get_report_builder_class(model=model, report_type=row_config.report_type)
        django_field, _, _, _ = self.get_field_details(
            base_model=model, field=row_config.group_field, report_builder_class=report_builder_class
        )
        return isinstance(django_field, DATE_FIELDS)

    def _distinct_row_specs(self, row_config):
        """The ordered list of row descriptors, one per generated row. A date group field yields
        period specs (``{'period': (start, end), 'value': None}``); any other field yields value specs
        (``{'period': None, 'value': v}``). Only groups that contain data, unless ``show_blank_dates``
        fills the empty periods between the first and last (date group fields only)."""
        if not row_config.report_type_id or not row_config.group_field:
            return []
        model = row_config.report_type.content_type.model_class()
        query = model.objects.all()
        if row_config.base_query:
            query = self.process_query_filters(query=query, search_filter_data=row_config.base_query)

        if not self._group_field_is_date(row_config):
            values = {
                value for value in query.values_list(row_config.group_field, flat=True).distinct() if value is not None
            }
            values = sorted(values, reverse=row_config.descending)[: row_config.limit]
            return [{'period': None, 'value': value} for value in values]

        trunc = ANNOTATION_VALUE_FUNCTIONS[row_config.period]
        period_starts = {
            start
            for start in query.annotate(_dyn_period=trunc(row_config.group_field))
            .values_list('_dyn_period', flat=True)
            .distinct()
            if start is not None
        }
        if not period_starts:
            return []
        if row_config.show_blank_dates:
            # Fill every period between the first and last, so empty periods render as blank rows.
            starts = []
            current, last = min(period_starts), max(period_starts)
            while current <= last and len(starts) < row_config.limit:
                starts.append(current)
                current = self._period_end(current, row_config.period)
        else:
            starts = period_starts
        starts = sorted(starts, reverse=row_config.descending)[: row_config.limit]
        return [{'period': (start, self._period_end(start, row_config.period)), 'value': None} for start in starts]

    @staticmethod
    def _period_end(start, period):
        if period == ANNOTATION_VALUE_DAY:
            return start + timedelta(days=1)
        if period == ANNOTATION_VALUE_MONTH:
            return MultiValueView._add_months(start, 1)
        if period == ANNOTATION_VALUE_QUARTER:
            return MultiValueView._add_months(start, 3)
        if period == ANNOTATION_VALUE_YEAR:
            return start.replace(year=start.year + 1, month=1, day=1)
        return start + timedelta(days=7)  # ANNOTATION_VALUE_WEEK (default)

    @staticmethod
    def _add_months(start, months):
        month_index = start.month - 1 + months
        year = start.year + month_index // 12
        month = month_index % 12 + 1
        return start.replace(year=year, month=month, day=1)

    def _dynamic_cell(self, template_cell, spec, row_config):
        """A per-group-value copy of a dynamic row's cell, limited to the row's value.

        The cell's metric is filtered on the group field it specifies (``group_field``), else the
        row's own ``group_field`` when the cell shares the row's report type - a date range for a
        period spec, an equality for a value spec. Static Text can reference the value via the
        ``{{ value }}`` / ``{{ period }}`` / ``{{ period_end }}`` merge variables (the row label).
        """
        cell = deepcopy(template_cell)
        group_field = template_cell.group_field
        if not group_field and template_cell.report_type_id == row_config.report_type_id:
            group_field = row_config.group_field
        if group_field:
            if spec['period'] is not None:
                cell.query_data = _and_period_filter(cell.query_data, group_field, *spec['period'])
            else:
                cell.query_data = _and_value_filter(cell.query_data, group_field, spec['value'])
        cell.text = apply_dynamic_merge(cell.text, spec, row_config.label_format)
        return cell

    def render_html(self, table_data):
        html = '<table class="table table-bordered kanban_summary">'

        columns_data = {}
        for multi_value_report_column in self.chart_report.multivaluereportcolumn_set.all():
            columns_data[multi_value_report_column.column] = multi_value_report_column.get_td_style()

        for row in table_data:
            html += '<tr>'
            for cols_index, cell in enumerate(row, start=1):
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
                    append_str = cell['append_str']
                    styles = []

                    if col_span == 1 and cols_index in columns_data:
                        styles.append(columns_data[cols_index])

                    if multi_value_report_cell.multi_cell_style is not None:
                        attrs.append('class="' + multi_value_report_cell.multi_cell_style.get_td_class() + '"')
                        styles.append(multi_value_report_cell.multi_cell_style.get_td_style())
                    link = self.get_breakdown_url(
                        multi_value_report_cell=multi_value_report_cell, spec=cell.get('spec')
                    )
                    if link is not None:
                        styles.append('cursor:pointer')
                        attrs.append(f'onclick="{link}"')

                    if len(styles) > 0:
                        attrs.append('style="' + ';'.join(styles) + '"')

                    attrs_html = ''
                    if len(attrs) > 0:
                        attrs_html = ' ' + ' '.join(attrs)

                    html += f'<td{attrs_html}>{value}{append_str}</td>'
            html += '</tr>'

        html += '</table>'
        return html

    def get_breakdown_url(self, multi_value_report_cell, spec=None):
        if multi_value_report_cell.show_breakdown:
            enable_links = self.kwargs.get('enable_links')
            slug = f'pk-{multi_value_report_cell.id}-enable_links-{enable_links}'
            if spec is not None and spec['period'] is not None:
                # Carry the row's period so the drill-down lists only that period's records
                # (compact yyyymmdd - the slug separator is '-', so no dashes in the value).
                start, end = spec['period']
                slug += f'-dyn_start-{start.strftime("%Y%m%d")}-dyn_end-{end.strftime("%Y%m%d")}'
            elif spec is not None and spec['value'] is not None:
                # Carry the row's value hex-encoded (slug-safe: no separators) so the drill-down
                # lists only that value's records.
                slug += f'-dyn_value-{str(spec["value"]).encode().hex()}'
            link = show_modal(
                'advanced_report_builder:multi_value_breakdown_modal',
                '',
                slug,
                href=True,
            )
            return link
        return None

    def pod_dashboard_edit_menu(self):
        return [
            MenuItem(
                f'advanced_report_builder:dashboard_report_modal,pk-{self.dashboard_report.id}',
                menu_display='Edit',
                font_awesome='fas fa-pencil-alt',
                css_classes=['btn-primary'],
            )
        ]

    def extra_filters(self, query):
        query_data = self.current_multi_value_report_cell.query_data
        extra_filter_data = None
        if self.current_multi_value_report_cell.multi_value_held_query is not None:
            extra_filter_data = self.current_multi_value_report_cell.multi_value_held_query.query
        if query_data:
            query = self.process_query_filters(
                query=query, search_filter_data=query_data, extra_filter_data=extra_filter_data
            )
        return query

    def _is_currency_field(self, multi_value_report_cell):
        from advanced_report_builder.column_types import CURRENCY_COLUMNS

        field_name = multi_value_report_cell.field
        if not field_name:
            return False
        base_model = multi_value_report_cell.get_base_model()
        if base_model is None:
            return False
        report_builder_class = get_report_builder_class(
            model=base_model, report_type=multi_value_report_cell.report_type
        )
        _, col_type_override, _, _ = self.get_field_details(
            base_model=base_model,
            field=field_name,
            report_builder_class=report_builder_class,
        )
        return isinstance(col_type_override, CURRENCY_COLUMNS)

    def set_prefix(self, table, multi_value_report_cell):
        from advanced_report_builder.globals import PREFIX_TYPE_CUSTOM, PREFIX_TYPE_NONE

        prefix_type = multi_value_report_cell.prefix_type
        if prefix_type == PREFIX_TYPE_NONE:
            table.prefix = ''
        elif prefix_type == PREFIX_TYPE_CUSTOM:
            table.prefix = multi_value_report_cell.prefix if multi_value_report_cell.prefix else ''
        else:
            if self._is_currency_field(multi_value_report_cell):
                table.prefix = self.get_currency_prefix()
            else:
                table.prefix = ''

    def render_value(self, base_model, fields, multi_value_report_cell):
        table = self.chart_js_table(model=base_model)
        self.set_prefix(table=table, multi_value_report_cell=multi_value_report_cell)
        table.add_columns(*fields)
        table.single_value = self.chart_report

        self.current_multi_value_report_cell = multi_value_report_cell

        table.extra_filters = self.extra_filters
        table.enable_links = self.kwargs.get('enable_links')
        table.datatable_template = 'advanced_report_builder/multi_values/middle.html'
        value = table.render()
        if len(table.raw_data) > 0 and len(table.raw_data[0]) > 0:
            return value, table.raw_data[0][0]
        return value, None


class MultiValueShowBreakdownModal(TableUtilsMixin, Modal):
    button_container_class = 'text-center'
    size = 'xl'

    def __init__(self, *args, **kwargs):
        self._held_multi_value_report_cell = None
        super().__init__(*args, **kwargs)

    def modal_title(self):
        multi_value_report_cell = self.get_multi_value_report_cell()
        title = multi_value_report_cell.label
        if title is None:
            title = excel_column_name(multi_value_report_cell.column, row=multi_value_report_cell.row)
        return f'{self.table_report.multi_value_report.name} - {title}'

    def add_table(self, base_model):
        return DatatableTable(view=self, model=base_model)

    def get_multi_value_report_cell(self):
        if self._held_multi_value_report_cell is None:
            self._held_multi_value_report_cell = get_object_or_404(MultiValueReportCell, pk=self.slug['pk'])
        return self._held_multi_value_report_cell

    def setup_table(self):
        multi_value_report_cell = self.get_multi_value_report_cell()
        self.kwargs['enable_links'] = self.slug['enable_links'] == 'True'
        self.table_report = multi_value_report_cell
        base_model = multi_value_report_cell.get_base_model()
        table = self.add_table(base_model=base_model)
        table.extra_filters = self.extra_filters
        table_fields = multi_value_report_cell.breakdown_fields
        report_builder_class = get_report_builder_class(model=base_model, report_type=self.table_report.report_type)
        fields_used = set()
        fields_map = {}
        try:
            self.process_query_results(
                report_builder_class=report_builder_class,
                table=table,
                base_model=base_model,
                fields_used=fields_used,
                fields_map=fields_map,
                table_fields=table_fields,
            )
        except (FieldError, FieldDoesNotExist) as e:
            raise ReportError(e)
        table.ajax_data = False
        table.table_options['pageLength'] = 25
        table.table_options['bStateSave'] = False
        if multi_value_report_cell.record_nav:
            table.add_plugin(RecordNavPlugin, self.modal_title())
        return table

    def modal_content(self):
        table = self.setup_table()
        return table.render()

    def extra_filters(self, query):
        multi_value_report_cell = self.get_multi_value_report_cell()
        query_data = multi_value_report_cell.query_data
        # Dynamic-row drill-down: the clicked row's group value arrives in the slug (a period range or
        # a hex value); limit the breakdown to it on the field the cell is filtered by (its own
        # group_field, else the row's when it shares the report type).
        dyn_start = self.slug.get('dyn_start')
        dyn_end = self.slug.get('dyn_end')
        dyn_value = self.slug.get('dyn_value')
        if dyn_start or dyn_value:
            group_field = multi_value_report_cell.group_field
            if not group_field:
                row_config = MultiValueReportRow.objects.filter(
                    multi_value_report_id=multi_value_report_cell.multi_value_report_id,
                    row=multi_value_report_cell.row,
                ).first()
                if row_config and row_config.report_type_id == multi_value_report_cell.report_type_id:
                    group_field = row_config.group_field
            if group_field and dyn_start and dyn_end:
                query_data = _and_period_filter(
                    query_data,
                    group_field,
                    datetime.strptime(dyn_start, '%Y%m%d'),
                    datetime.strptime(dyn_end, '%Y%m%d'),
                )
            elif group_field and dyn_value:
                query_data = _and_value_filter(query_data, group_field, bytes.fromhex(dyn_value).decode())
        extra_filter_data = None
        if multi_value_report_cell.multi_value_held_query is not None:
            extra_filter_data = multi_value_report_cell.multi_value_held_query.query
        if query_data:
            query = self.process_query_filters(
                query=query, search_filter_data=query_data, extra_filter_data=extra_filter_data
            )
        return query

    def get_report_query(self, report):
        return self.get_multi_value_report_cell()


class MultiValueCellCopyFromModal(FormModal):
    form_class = CrispyForm
    modal_title = 'Copy Cell From'

    def __init__(self, *args, **kwargs):
        self._held_multi_value_report = None
        super().__init__(*args, **kwargs)

    def get_multi_value_report(self):
        if self._held_multi_value_report is None:
            self._held_multi_value_report = get_object_or_404(MultiValueReport, pk=self.slug['pk'])
        return self._held_multi_value_report

    def form_setup(self, form, *_args, **_kwargs):
        multi_value_report = self.get_multi_value_report()
        multi_value_report_cells = MultiValueReportCell.objects.filter(multi_value_report=multi_value_report)
        form.fields['copy_from'] = ModelChoiceField(queryset=multi_value_report_cells, widget=Select2())
        form.fields['copy_from'].label_from_instance = self.label_from_instance

    @staticmethod
    def label_from_instance(obj):
        return excel_column_name(obj.column, row=obj.row)

    def form_valid(self, form):
        original_cell = form.cleaned_data['copy_from']
        multi_value_report_cell = deepcopy(original_cell)
        multi_value_report_cell.pk = None
        multi_value_report_cell.id = None
        multi_value_report_cell.row = int(self.slug['row'])
        multi_value_report_cell.column = int(self.slug['column'])
        multi_value_report_cell.save()
        return self.command_response('reload')


class MultiValueTableFieldForm(TableFieldForm):
    cancel_class = 'btn-secondary modal-cancel'

    def cancel_button(self, css_class=cancel_class, **kwargs):
        commands = [
            {'function': 'save_query_builder_id_query_data'},
            {'function': 'save_query_builder_id_extra_query_data'},
            {'function': 'close'},
        ]
        return self.button('Cancel', commands, css_class, **kwargs)


class MultiValueTableFieldModal(TableFieldModal):
    form_class = MultiValueTableFieldForm

    def form_valid(self, form):
        selector = self.slug['selector']

        _attr = form.get_additional_attributes()
        self.add_command({'function': 'set_attr', 'selector': f'#{selector}', 'attr': 'data-attr', 'val': _attr})

        self.add_command({'function': 'html', 'selector': f'#{selector} span', 'html': form.cleaned_data['title']})
        self.add_command({'function': 'save_query_builder_id_query_data'})
        self.add_command({'function': 'save_query_builder_id_extra_query_data'})
        self.add_command({'function': 'update_selection'})
        return self.command_response('close')
