import base64
import json
import operator
from datetime import datetime, timedelta
from functools import reduce

from crispy_forms.bootstrap import StrictButton
from crispy_forms.layout import Div
from date_offset.monthdelta import MonthDelta
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Q
from django.forms import BooleanField, CharField, ChoiceField
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django_datatables.datatables import DatatableTable
from django_menus.menu import MenuItem
from django_modals.fields import FieldEx
from django_modals.form_helpers import HorizontalNoEnterHelper
from django_modals.modals import FormModal, Modal
from django_modals.processes import PERMISSION_OFF, PROCESS_EDIT_DELETE
from django_modals.widgets.colour_picker import ColourPickerWidget
from django_modals.widgets.select2 import Select2, Select2Multiple
from django_modals.widgets.widgets import Toggle

from advanced_report_builder.column_types import NUMBER_FIELDS
from advanced_report_builder.exceptions import ReportError
from advanced_report_builder.generate_series import GenerateSeries
from advanced_report_builder.globals import (
    ANNOTATION_VALUE_DAY,
    ANNOTATION_VALUE_FUNCTIONS,
    ANNOTATION_VALUE_MONTH,
    ANNOTATION_VALUE_QUARTER,
    ANNOTATION_VALUE_WEEK,
    ANNOTATION_VALUE_YEAR,
    DATE_FORMAT_TYPES_DJANGO_FORMAT,
    DEFAULT_DATE_FORMAT,
    GENERATE_SERIES_INTERVALS,
)
from advanced_report_builder.models import BarChartReport, ReportType
from advanced_report_builder.toggle import RBToggle
from advanced_report_builder.utils import (
    decode_attribute,
    encode_attribute,
    get_report_builder_class,
    split_attr,
)
from advanced_report_builder.views.charts_base import ChartBaseFieldForm, ChartBaseView
from advanced_report_builder.views.datatables.modal import (
    TableFieldForm,
    TableFieldModal,
)
from advanced_report_builder.views.datatables.utils import TableUtilsMixin
from advanced_report_builder.views.modals_base import (
    QueryBuilderModalBase,
    QueryBuilderModalBaseMixin,
)
from advanced_report_builder.views.query_modal.mixin import MultiQueryModalMixin


class BarChartView(ChartBaseView):
    def dispatch(self, request, *args, **kwargs):
        self.report = kwargs.get('report')
        self.chart_report = self.report.barchartreport
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        try:
            context = super().get_context_data(**kwargs)
        except FieldDoesNotExist as e:
            raise ReportError(e)
        self.table.bar_chart_report = self.chart_report
        self.table.datatable_template = 'advanced_report_builder/charts/bar/middle.html'
        self.table.breakdown_url = self.get_breakdown_url()

        context['bar_chart_report'] = self.chart_report
        return context

    def get_breakdown_url(self):
        if self.table.bar_chart_report.show_breakdown:
            enable_links = self.slug.get('enable_links') == 'True'
            slug = f'pk-{self.table.bar_chart_report.id}-data-99999-date-88888-enable_links-{enable_links}'
            return reverse(
                'advanced_report_builder:bar_chart_show_breakdown_modal',
                kwargs={'slug': slug},
            )
        return None

    def get_date_format(self):
        if self.chart_report.show_blank_dates:
            date_format = '%Y-%m-%d'
        else:
            default_format_type = DEFAULT_DATE_FORMAT[self.chart_report.axis_scale]
            date_format = DATE_FORMAT_TYPES_DJANGO_FORMAT[default_format_type]
        return date_format

    def set_extra_number_field_kwargs(self, data_attr, options, multiple_index, additional_options):
        negative_bar_colour = None
        positive_bar_colour = None
        if additional_options is not None:
            negative_bar_colour = additional_options.get('negative_colour')
            positive_bar_colour = additional_options.get('positive_colour')
        if negative_bar_colour is None or negative_bar_colour == '':
            negative_bar_colour = data_attr.get('negative_bar_colour') or '801C70'
            negative_bar_colour = self.add_colour_offset(negative_bar_colour, multiple_index=multiple_index)
        if positive_bar_colour is None or positive_bar_colour == '':
            positive_bar_colour = data_attr.get('positive_bar_colour') or '801C70'
            positive_bar_colour = self.add_colour_offset(positive_bar_colour, multiple_index=multiple_index)

        options.update(
            {
                'colours': {
                    'negative': negative_bar_colour,
                    'positive': positive_bar_colour,
                }
            }
        )

    def edit_report_menu(self, request, chart_report_id, slug_str):
        return [
            MenuItem(
                f'advanced_report_builder:bar_chart_modal,pk-{chart_report_id}{slug_str}',
                menu_display='Edit',
                font_awesome='fas fa-pencil-alt',
                css_classes=['btn-primary'],
            ),
            *self.duplicate_menu(request=self.request, report_id=chart_report_id),
        ]

    def get_date_field(self, index, fields, base_model, table):
        if self.chart_report.date_field_type == BarChartReport.DATE_FIELD_SINGLE:
            return super().get_date_field(index=index, fields=fields, base_model=base_model, table=table)

        start_field_name = self.chart_report.date_field
        end_field_name = self.chart_report.end_date_field

        if start_field_name is None or end_field_name is None:
            return

        report_builder_class = get_report_builder_class(model=base_model, report_type=self.chart_report.report_type)

        start_django_field, start_col_type_override, _, _ = self.get_field_details(
            base_model=base_model,
            field=start_field_name,
            report_builder_class=report_builder_class,
            table=table,
        )
        if start_col_type_override:
            start_field_name = start_col_type_override.field

        end_django_field, end_col_type_override, _, _ = self.get_field_details(
            base_model=base_model,
            field=end_field_name,
            report_builder_class=report_builder_class,
            table=table,
        )
        if end_col_type_override:
            end_field_name = end_col_type_override.field

        date_format = self.get_date_format()

        date_function_kwargs = {'title': start_field_name, 'date_format': date_format}

        annotations_value = self.chart_report.axis_scale

        new_field_name = f'{annotations_value}_{start_field_name}_{index}'
        function = ANNOTATION_VALUE_FUNCTIONS[annotations_value]
        date_function_kwargs['annotations_value'] = {
            new_field_name: GenerateSeries(
                start_date_field=function(start_field_name),
                end_date_field=function(end_field_name),
                interval=GENERATE_SERIES_INTERVALS[annotations_value],
            )
        }
        start_field_name = new_field_name

        date_function_kwargs.update(
            {
                'field': start_field_name,
                'column_name': start_field_name,
                'model_path': '',
            }
        )

        field = self.date_field(**date_function_kwargs)
        fields.append(field)
        return start_field_name


class BarChartModal(MultiQueryModalMixin, QueryBuilderModalBase):
    template_name = 'advanced_report_builder/charts/modal.html'
    process = PROCESS_EDIT_DELETE
    permission_delete = PERMISSION_OFF
    model = BarChartReport
    show_order_by = False
    widgets = {
        'positive_bar_colour': ColourPickerWidget,
        'negative_bar_colour': ColourPickerWidget,
        'stacked': RBToggle,
        'show_totals': RBToggle,
        'show_blank_dates': RBToggle,
        'date_field_type': Select2,
        'report_tags': Select2Multiple,
        'show_breakdown': Toggle(attrs={'data-onstyle': 'success', 'data-on': 'YES', 'data-off': 'NO'}),
    }

    form_fields = [
        'name',
        'notes',
        'report_type',
        'report_tags',
        ('bar_chart_orientation', {'label': 'Orientation'}),
        'axis_value_type',
        'axis_scale',
        'date_field_type',
        'date_field',
        'end_date_field',
        'fields',
        'x_label',
        'y_label',
        'stacked',
        'show_totals',
        'show_blank_dates',
        'show_breakdown',
        'breakdown_fields',
    ]

    def form_setup(self, form, *_args, **_kwargs):
        if 'data' in _kwargs and len(_kwargs['data']) > 0:
            date_field = _kwargs['data'].get('date_field')
            end_date_field = _kwargs['data'].get('end_date_field')
            report_type_id = _kwargs['data'].get('report_type')
            report_type = get_object_or_404(ReportType, id=report_type_id)
        else:
            date_field = form.instance.date_field
            end_date_field = form.instance.end_date_field
            report_type = form.instance.report_type

        self.setup_field(
            field_type='date',
            form=form,
            field_name='date_field',
            selected_field_id=date_field,
            report_type=report_type,
        )

        self.setup_field(
            field_type='date',
            form=form,
            field_name='end_date_field',
            selected_field_id=end_date_field,
            report_type=report_type,
        )

        form.fields['notes'].widget.attrs['rows'] = 3

        url = reverse(
            'advanced_report_builder:bar_chart_field_modal',
            kwargs={'slug': 'selector-99999-data-FIELD_INFO-report_type_id-REPORT_TYPE_ID'},
        )

        url_breakdown = reverse(
            'advanced_report_builder:bar_chart_breakdown_field_modal',
            kwargs={'slug': 'selector-99999-data-FIELD_INFO-report_type_id-REPORT_TYPE_ID'},
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

        form.add_trigger(
            'date_field_type',
            'onchange',
            [
                {
                    'selector': '#div_id_end_date_field',
                    'values': {BarChartReport.DATE_FIELD_RANGE: 'show'},
                    'default': 'hide',
                },
                {
                    'selector': 'label[for=id_date_field]',
                    'values': {
                        BarChartReport.DATE_FIELD_SINGLE: ('html', 'Date field'),
                        BarChartReport.DATE_FIELD_RANGE: ('html', 'Start date field'),
                    },
                },
            ],
        )

        fields = [
            'name',
            'notes',
            'report_type',
            'report_tags',
            'bar_chart_orientation',
            'axis_scale',
            'axis_value_type',
            'date_field_type',
            'date_field',
            'end_date_field',
            FieldEx(
                'fields',
                template='advanced_report_builder/select_column.html',
                extra_context={'select_column_url': url, 'command_prefix': ''},
            ),
            'x_label',
            'y_label',
            'stacked',
            'show_totals',
            'show_blank_dates',
            'show_breakdown',
            FieldEx(
                'breakdown_fields',
                template='advanced_report_builder/select_column.html',
                extra_context={
                    'select_column_url': url_breakdown,
                    'command_prefix': 'breakdown_',
                },
            ),
        ]
        if self.object.id:
            self.add_extra_queries(form=form, fields=fields)
        return fields

    def select2_date_field(self, **kwargs):
        return self.get_fields_for_select2(
            field_type='date',
            report_type=kwargs['report_type'],
            search_string=kwargs.get('search'),
        )

    def select2_end_date_field(self, **kwargs):
        return self.select2_date_field(**kwargs)

    def _get_ajax_fields(self, report_type, prefix=''):
        report_type_id = report_type
        report_builder_fields, base_model = self.get_report_builder_class(report_type_id=report_type_id)
        fields = []
        tables = []
        self._get_fields(
            base_model=base_model,
            fields=fields,
            tables=tables,
            report_builder_class=report_builder_fields,
        )

        self.add_command(
            f'{prefix}report_fields',
            data=json.dumps({'fields': fields, 'tables': tables}),
        )
        return self.command_response()

    def ajax_get_fields(self, **kwargs):
        return self._get_ajax_fields(report_type=kwargs['report_type'])

    def ajax_get_breakdown_fields(self, **kwargs):
        return self._get_ajax_fields(report_type=kwargs['report_type'], prefix='breakdown_')

    def clean(self, form, cleaned_data):
        end_date_field = cleaned_data['end_date_field']
        if cleaned_data['date_field_type'] == BarChartReport.DATE_FIELD_RANGE and (
            end_date_field is None or end_date_field == ''
        ):
            form.add_error('end_date_field', 'Please select a date')


class BarChartFieldForm(ChartBaseFieldForm):
    def setup_modal(self, *args, **kwargs):
        data = json.loads(base64.b64decode(self.slug['data']))
        report_type, base_model = self.get_report_type_details()

        data_attr = split_attr(data)

        self.fields['title'] = CharField(initial=data['title'])

        self.fields['positive_bar_colour'] = CharField(required=False, widget=ColourPickerWidget)
        self.fields['negative_bar_colour'] = CharField(required=False, widget=ColourPickerWidget)
        self.fields['positive_bar_colour'].initial = data_attr.get('positive_bar_colour')
        self.fields['negative_bar_colour'].initial = data_attr.get('negative_bar_colour')

        self.fields['has_filter'] = BooleanField(required=False, widget=RBToggle())
        self.fields['filter'] = CharField(required=False)

        if data_attr.get('has_filter') == '1':
            self.fields['has_filter'].initial = True
            if 'filter' in data_attr:
                self.fields['filter'].initial = decode_attribute(data_attr['filter'])

        self.fields['multiple_columns'] = BooleanField(required=False, widget=RBToggle())
        self.fields['append_column_title'] = BooleanField(required=False, widget=RBToggle())
        report_builder_class = get_report_builder_class(model=base_model, report_type=report_type)

        self.setup_colour_field(
            form_fields=self.fields,
            base_model=base_model,
            report_builder_class=report_builder_class,
            name='positive_colour_field',
            data_attr=data_attr,
        )
        self.setup_colour_field(
            form_fields=self.fields,
            base_model=base_model,
            report_builder_class=report_builder_class,
            name='negative_colour_field',
            data_attr=data_attr,
        )

        multiple_column_field = []
        self._get_query_builder_foreign_key_fields(
            base_model=base_model,
            report_builder_class=report_builder_class,
            fields=multiple_column_field,
        )
        self.fields['multiple_column_field'] = ChoiceField(
            choices=multiple_column_field, required=False, widget=Select2()
        )

        if data_attr.get('multiple_columns') == '1':
            self.fields['multiple_columns'].initial = True
            self.fields['multiple_column_field'].initial = data_attr.get('multiple_column_field')

            if data_attr.get('append_column_title') == '1':
                self.fields['append_column_title'].initial = True

        super().setup_modal(*args, **kwargs)

    def get_additional_attributes(self):
        attributes = []
        self.get_report_type_details()

        attributes.append(f'positive_bar_colour-{self.cleaned_data["positive_bar_colour"]}')
        attributes.append(f'negative_bar_colour-{self.cleaned_data["negative_bar_colour"]}')

        if self.cleaned_data['has_filter']:
            attributes.append('has_filter-1')

            if self.cleaned_data['filter']:
                b64_filter = encode_attribute(self.cleaned_data['filter'])
                attributes.append(f'filter-{b64_filter}')

            if self.cleaned_data['multiple_columns']:
                attributes.append('multiple_columns-1')

                if self.cleaned_data['multiple_column_field']:
                    attributes.append(f'multiple_column_field-{self.cleaned_data["multiple_column_field"]}')

                if self.cleaned_data['append_column_title']:
                    attributes.append('append_column_title-1')

                if self.cleaned_data['positive_colour_field']:
                    attributes.append(f'positive_colour_field-{self.cleaned_data["positive_colour_field"]}')

                if self.cleaned_data['negative_colour_field']:
                    attributes.append(f'negative_colour_field-{self.cleaned_data["negative_colour_field"]}')

        if attributes:
            return '-'.join(attributes)
        return None


class BarChartFieldModal(QueryBuilderModalBaseMixin, FormModal):
    form_class = BarChartFieldForm
    size = 'xl'
    template_name = 'advanced_report_builder/charts/modal_field.html'
    no_header_x = True
    helper_class = HorizontalNoEnterHelper

    @property
    def modal_title(self):
        data = json.loads(base64.b64decode(self.slug['data']))
        return f'Edit {data["title"]}'

    def form_valid(self, form):
        selector = self.slug['selector']

        _attr = form.get_additional_attributes()
        self.add_command(
            {
                'function': 'set_attr',
                'selector': f'#{selector}',
                'attr': 'data-attr',
                'val': _attr,
            }
        )

        self.add_command(
            {
                'function': 'html',
                'selector': f'#{selector} span',
                'html': form.cleaned_data['title'],
            }
        )
        self.add_command({'function': 'update_selection'})
        return self.command_response('close')

    # noinspection PyMethodMayBeStatic
    def form_setup(self, form, *_args, **_kwargs):
        form.add_trigger(
            'has_filter',
            'onchange',
            [
                {
                    'selector': '#filter_fields_div',
                    'values': {'checked': 'show'},
                    'default': 'hide',
                }
            ],
        )

        form.add_trigger(
            'multiple_columns',
            'onchange',
            [
                {
                    'selector': '#multiple_columns_fields_div',
                    'values': {'checked': 'show'},
                    'default': 'hide',
                },
            ],
        )

        return [
            'title',
            'positive_bar_colour',
            'negative_bar_colour',
            Div(
                FieldEx(
                    'has_filter',
                    template='django_modals/fields/label_checkbox.html',
                    field_class='col-6 input-group-sm',
                ),
                Div(
                    FieldEx(
                        'filter',
                        template='advanced_report_builder/datatables/fields/single_query_builder.html',
                    ),
                    FieldEx(
                        'multiple_columns',
                        template='django_modals/fields/label_checkbox.html',
                        field_class='col-6 input-group-sm',
                    ),
                    Div(
                        FieldEx(
                            'append_column_title',
                            template='django_modals/fields/label_checkbox.html',
                            field_class='col-6 input-group-sm',
                        ),
                        FieldEx('multiple_column_field'),
                        FieldEx('positive_colour_field'),
                        FieldEx('negative_colour_field'),
                        css_id='multiple_columns_fields_div',
                    ),
                    css_id='filter_fields_div',
                ),
                css_id='annotations_fields_div',
            ),
        ]

    def ajax_get_query_builder_fields(self, **kwargs):
        field_auto_id = kwargs['field_auto_id']

        report_type_id = self.slug['report_type_id']
        query_builder_filters = self.get_query_builder_report_type_field(report_type_id=report_type_id)

        return self.command_response(f'query_builder_{field_auto_id}', data=json.dumps(query_builder_filters))


class BarChartBreakdownFieldForm(TableFieldForm):
    cancel_class = 'btn-secondary modal-cancel'

    def submit_button(self, css_class='btn-success modal-submit', button_text='Submit', **kwargs):
        if isinstance(self.django_field, NUMBER_FIELDS):
            return StrictButton(
                button_text,
                onclick=f'save_modal_{self.form_id}()',
                css_class=css_class,
                **kwargs,
            )
        else:
            return super().submit_button(css_class, button_text, **kwargs)


class BarChartBreakdownFieldModal(TableFieldModal):
    form_class = BarChartBreakdownFieldForm
    update_selection_command = 'breakdown_update_selection'


class BarChartShowBreakdownModal(TableUtilsMixin, Modal):
    button_container_class = 'text-center'
    size = 'xl'

    def __init__(self, *args, **kwargs):
        self.date_field_path = None
        self.end_date_field_path = None
        self.bar_chart_report = None
        self.chart_report = None
        self.field_filter = None
        super().__init__(*args, **kwargs)

    def get_bar_chart_report(self):
        if self.bar_chart_report is None:
            self.bar_chart_report = get_object_or_404(BarChartReport, pk=self.slug['pk'])
        return self.bar_chart_report

    def modal_title(self):
        bar_chart_report = self.get_bar_chart_report()

        data_index = int(self.slug['data'])
        field = bar_chart_report.fields[data_index]
        title = field['title']
        date_title = self.get_date_title()
        return f'{bar_chart_report.name} - {title} - {date_title}'

    def add_table(self, base_model):
        return DatatableTable(view=self, model=base_model)

    def setup_table(self):
        bar_chart_report = self.get_bar_chart_report()
        self.chart_report = bar_chart_report
        self.kwargs['enable_links'] = self.slug['enable_links'] == 'True'
        base_model = bar_chart_report.get_base_model()
        chart_fields = bar_chart_report.fields
        report_builder_class = get_report_builder_class(model=base_model, report_type=bar_chart_report.report_type)
        table = self.add_table(base_model=base_model)

        table_fields = bar_chart_report.breakdown_fields
        fields_used = set()
        fields_map = {}
        self.process_query_results(
            report_builder_class=report_builder_class,
            table=table,
            base_model=base_model,
            fields_used=fields_used,
            fields_map=fields_map,
            table_fields=table_fields,
        )
        data_index = int(self.slug['data'])
        table_field = chart_fields[data_index]
        field = table_field['field']
        django_field, col_type_override, _, _ = self.get_field_details(
            base_model=base_model,
            field=field,
            report_builder_class=report_builder_class,
            table=table,
        )

        self.field_filter = None
        if isinstance(django_field, NUMBER_FIELDS) or (col_type_override is not None and col_type_override.annotations):
            data_attr = split_attr(table_field)

            annotations_type = self.chart_report.axis_value_type
            if annotations_type != 0:
                b64_filter = data_attr.get('filter')
                if b64_filter:
                    _filter = decode_attribute(b64_filter)
                    self.field_filter = json.loads(_filter)

        self.date_field_path = self.get_field_details(
            base_model=base_model,
            field=bar_chart_report.date_field,
            report_builder_class=report_builder_class,
            table=table,
        )[3]
        if bar_chart_report.date_field_type == BarChartReport.DATE_FIELD_RANGE:
            self.end_date_field_path = self.get_field_details(
                base_model=base_model,
                field=bar_chart_report.end_date_field,
                report_builder_class=report_builder_class,
                table=table,
            )[3]

        table.extra_filters = self.extra_filters

        table.ajax_data = False
        table.table_options['pageLength'] = 25
        table.table_options['bStateSave'] = False
        return table

    def modal_content(self):
        table = self.setup_table()
        return table.render()

    def get_date_title(self):
        bar_chart_report = self.bar_chart_report
        start_date = datetime.strptime(self.slug['date'], '%Y_%m_%d').date()

        if bar_chart_report.axis_scale == ANNOTATION_VALUE_YEAR:
            return start_date.year
        elif bar_chart_report.axis_scale in [
            ANNOTATION_VALUE_QUARTER,
            ANNOTATION_VALUE_MONTH,
        ]:
            return start_date.strftime('%b %Y')
        elif bar_chart_report.axis_scale == ANNOTATION_VALUE_WEEK:
            end_date = start_date + timedelta(weeks=1)
            return start_date.strftime('%d/%m/%Y') + ' - ' + end_date.strftime('%d/%b/%Y')

        elif bar_chart_report.axis_scale == ANNOTATION_VALUE_DAY:
            return start_date.strftime('%d/%m/%Y')
        else:
            raise AssertionError()

    def filter_date(self, query):
        bar_chart_report = self.chart_report
        start_date = datetime.strptime(self.slug['date'], '%Y_%m_%d').date()

        if bar_chart_report.axis_scale == ANNOTATION_VALUE_YEAR:
            end_date = start_date + MonthDelta(months=12)
        elif bar_chart_report.axis_scale == ANNOTATION_VALUE_QUARTER:
            end_date = start_date + MonthDelta(months=3)
        elif bar_chart_report.axis_scale == ANNOTATION_VALUE_MONTH:
            end_date = start_date + MonthDelta(months=1)
        elif bar_chart_report.axis_scale == ANNOTATION_VALUE_WEEK:
            end_date = start_date + timedelta(weeks=1)
        elif bar_chart_report.axis_scale == ANNOTATION_VALUE_DAY:
            end_date = start_date + timedelta(days=1)
        else:
            raise AssertionError()

        if self.end_date_field_path is None:
            query_list = [
                (Q((self.date_field_path + '__gte', start_date))) & (Q((self.date_field_path + '__lt', end_date)))
            ]
        else:
            query_list = [
                (Q((self.date_field_path + '__lt', end_date))) & (Q((self.end_date_field_path + '__gte', start_date)))
            ]

        return query.filter(reduce(operator.and_, query_list))

    def extra_filters(self, query):
        report_query = self.get_report_query(report=self.chart_report)
        if report_query:
            query = self.process_query_filters(query=query, search_filter_data=report_query.query)
        if self.field_filter is not None:
            query = self.process_query_filters(query=query, search_filter_data=self.field_filter)

        query = self.filter_date(query=query)
        return query
