import base64
import json
from datetime import datetime

from crispy_forms.layout import Div
from date_offset.date_offset import DateOffset
from django.forms import BooleanField, CharField, ChoiceField
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django_menus.menu import MenuItem
from django_modals.fields import FieldEx
from django_modals.form_helpers import HorizontalNoEnterHelper
from django_modals.modals import FormModal
from django_modals.processes import PERMISSION_OFF, PROCESS_EDIT_DELETE
from django_modals.widgets.colour_picker import ColourPickerWidget
from django_modals.widgets.select2 import Select2Multiple

from advanced_report_builder.exceptions import ReportError
from advanced_report_builder.globals import (
    ANNOTATION_VALUE_DAY,
    ANNOTATION_VALUE_MONTH,
    ANNOTATION_VALUE_QUARTER,
    ANNOTATION_VALUE_WEEK,
    ANNOTATION_VALUE_YEAR,
)
from advanced_report_builder.models import LineChartReport, ReportType
from advanced_report_builder.toggle import RBToggle
from advanced_report_builder.utils import (
    decode_attribute,
    encode_attribute,
    get_report_builder_class,
    split_attr,
)
from advanced_report_builder.views.charts_base import (
    ChartBaseFieldForm,
    ChartBaseView,
    ChartJSTable,
)
from advanced_report_builder.views.modals_base import (
    QueryBuilderModalBase,
    QueryBuilderModalBaseMixin,
)
from advanced_report_builder.views.query_modal.mixin import MultiQueryModalMixin


class LineChartJSTable(ChartJSTable):
    def get_table_array(self, request, results):
        results = super().get_table_array(request, results)
        if len(results) == 0:
            return results

        date_offset = DateOffset()
        record_count = len(results[0]) - 1
        try:
            next_date = datetime.strptime(results[0][0], '%Y-%m-%d').date()
        except ValueError as e:
            raise ReportError(e)

        new_results = []
        for record in results:
            if record[0] == '' or record[0] is None:
                continue
            current_date = datetime.strptime(record[0], '%Y-%m-%d').date()
            if current_date != next_date:
                while next_date < current_date:
                    row = [next_date.strftime('%Y-%m-%d')] + ['0' for _ in range(record_count)]
                    new_results.append(row)
                    next_date = self.get_next_date(date_offset, date_in=next_date)

            row = [record[0]]
            for x in record[1:]:
                if x == '':
                    row.append('')
                else:
                    row.append(x)
            new_results.append(row)
            next_date = self.get_next_date(date_offset, date_in=next_date)

        return new_results

    def get_next_date(self, date_offset, date_in):
        if self.axis_scale == ANNOTATION_VALUE_YEAR:
            next_date = date_offset.get_offset('1y', start_date_time=date_in)
        elif self.axis_scale == ANNOTATION_VALUE_QUARTER:
            next_date = date_offset.get_offset('3m', start_date_time=date_in)
        elif self.axis_scale == ANNOTATION_VALUE_MONTH:
            next_date = date_offset.get_offset('1m', start_date_time=date_in)
        elif self.axis_scale == ANNOTATION_VALUE_WEEK:
            next_date = date_offset.get_offset('1w', start_date_time=date_in)
        elif self.axis_scale == ANNOTATION_VALUE_DAY:
            next_date = date_offset.get_offset('1d', start_date_time=date_in)
        else:
            raise AssertionError()
        return next_date


class LineChartView(ChartBaseView):
    chart_js_table = LineChartJSTable

    def dispatch(self, request, *args, **kwargs):
        self.report = kwargs.get('report')
        self.chart_report = self.report.linechartreport
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.table.line_chart_report = self.chart_report
        self.table.datatable_template = 'advanced_report_builder/charts/line/middle.html'
        context['line_chart_report'] = self.chart_report
        return context

    def set_extra_number_field_kwargs(self, data_attr, options, multiple_index, additional_options):
        line_colour = None
        if additional_options is not None:
            line_colour = additional_options.get('positive_colour')
        if line_colour is None or line_colour == '':
            line_colour = data_attr.get('line_colour') or '801C70'
            line_colour = self.add_colour_offset(line_colour, multiple_index=multiple_index)
        options.update({'colour': line_colour})

    def edit_report_menu(self, request, chart_report_id, slug_str):
        return [
            MenuItem(
                f'advanced_report_builder:line_chart_modal,pk-{chart_report_id}{slug_str}',
                menu_display='Edit',
                font_awesome='fas fa-pencil-alt',
                css_classes=['btn-primary'],
            ),
            *self.duplicate_menu(request=self.request, report_id=chart_report_id),
        ]

    def setup_table(self, base_model):
        axis_scale = self.chart_report.axis_scale
        targets = None

        if getattr(self.chart_report, 'has_targets', False):
            targets = self.chart_report.targets
        self.table = self.chart_js_table(model=base_model, axis_scale=axis_scale, targets=targets)


class LineChartModal(MultiQueryModalMixin, QueryBuilderModalBase):
    template_name = 'advanced_report_builder/charts/modal.html'
    process = PROCESS_EDIT_DELETE
    permission_delete = PERMISSION_OFF
    model = LineChartReport
    show_order_by = False

    widgets = {
        'line_colour': ColourPickerWidget,
        'show_totals': RBToggle,
        'has_targets': RBToggle,
        'report_tags': Select2Multiple,
        'targets': Select2Multiple,
    }

    form_fields = [
        'name',
        'notes',
        'report_type',
        'report_tags',
        'axis_value_type',
        'axis_scale',
        'date_field',
        'fields',
        'x_label',
        'y_label',
        'show_totals',
        'has_targets',
        'targets',
    ]

    def form_setup(self, form, *_args, **_kwargs):
        form.add_trigger(
            'has_targets',
            'onchange',
            [
                {
                    'selector': '#div_id_targets',
                    'values': {'checked': 'show'},
                    'default': 'hide',
                },
            ],
        )

        if 'data' in _kwargs and len(_kwargs['data']) > 0:
            date_field = _kwargs['data'].get('date_field')
            report_type_id = _kwargs['data'].get('report_type')
            report_type = get_object_or_404(ReportType, id=report_type_id)
        else:
            date_field = form.instance.date_field
            report_type = form.instance.report_type

        self.setup_field(
            field_type='date',
            form=form,
            field_name='date_field',
            selected_field_id=date_field,
            report_type=report_type,
        )

        form.fields['notes'].widget.attrs['rows'] = 3

        url = reverse(
            'advanced_report_builder:line_chart_field_modal',
            kwargs={'slug': 'selector-99999-data-FIELD_INFO-report_type_id-REPORT_TYPE_ID'},
        )

        fields = [
            'name',
            'notes',
            'report_type',
            'report_tags',
            'axis_scale',
            'axis_value_type',
            'date_field',
            FieldEx(
                'fields',
                template='advanced_report_builder/select_column.html',
                extra_context={'select_column_url': url, 'command_prefix': ''},
            ),
            'x_label',
            'y_label',
            'show_totals',
            'has_targets',
            'targets',
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


class LineChartFieldForm(ChartBaseFieldForm):
    def setup_modal(self, *args, **kwargs):
        data = json.loads(base64.b64decode(self.slug['data']))
        report_type, base_model = self.get_report_type_details()

        data_attr = split_attr(data)

        self.fields['title'] = CharField(initial=data['title'])

        self.fields['line_colour'] = CharField(required=False, widget=ColourPickerWidget)
        self.fields['line_colour'].initial = data_attr.get('line_colour')

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
            label='Line colour field',
        )
        multiple_column_field = []
        self._get_query_builder_foreign_key_fields(
            base_model=base_model,
            report_builder_class=report_builder_class,
            fields=multiple_column_field,
        )

        self.fields['multiple_column_field'] = ChoiceField(choices=multiple_column_field, required=False)

        if data_attr.get('multiple_columns') == '1':
            self.fields['multiple_columns'].initial = True
            self.fields['multiple_column_field'].initial = data_attr.get('multiple_column_field')

            if data_attr.get('append_column_title') == '1':
                self.fields['append_column_title'].initial = True

        super().setup_modal(*args, **kwargs)

    def get_additional_attributes(self):
        attributes = []
        self.get_report_type_details()

        attributes.append(f'line_colour-{self.cleaned_data["line_colour"]}')

        if self.cleaned_data['has_filter']:
            attributes.append('has_filter-1')

            if self.cleaned_data['filter']:
                b64_filter = encode_attribute(self.cleaned_data['filter'])
                attributes.append(f'filter-{b64_filter}')
            if self.cleaned_data['multiple_columns']:
                attributes.append('multiple_columns-1')
                if self.cleaned_data['positive_colour_field']:
                    attributes.append(f'positive_colour_field-{self.cleaned_data["positive_colour_field"]}')
                attributes.append(f'multiple_column_field-{self.cleaned_data["multiple_column_field"]}')
                if self.cleaned_data['append_column_title']:
                    attributes.append('append_column_title-1')

        if attributes:
            return '-'.join(attributes)
        return None


class LineChartFieldModal(QueryBuilderModalBaseMixin, FormModal):
    form_class = LineChartFieldForm
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
            'line_colour',
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
