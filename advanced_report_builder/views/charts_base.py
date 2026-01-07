import base64
import copy
import json
import math
from datetime import datetime, timedelta

from date_offset.date_offset import DateOffset
from dateutil.relativedelta import relativedelta
from django.apps import apps
from django.core.exceptions import FieldDoesNotExist, FieldError
from django.db import DataError, ProgrammingError
from django.db.models import Q
from django.forms import ChoiceField
from django.shortcuts import get_object_or_404
from django.utils.safestring import mark_safe
from django.views.generic import TemplateView
from django_datatables.datatables import DatatableTable
from django_menus.menu import MenuItem
from django_modals.widgets.select2 import Select2

from advanced_report_builder.column_types import NUMBER_FIELDS
from advanced_report_builder.columns import ReportBuilderDateColumn
from advanced_report_builder.exceptions import ReportError
from advanced_report_builder.field_utils import ReportBuilderFieldUtils
from advanced_report_builder.globals import (
    ANNOTATION_VALUE_DAY,
    ANNOTATION_VALUE_FINANCIAL_QUARTER,
    ANNOTATION_VALUE_FUNCTIONS,
    ANNOTATION_VALUE_MONTH,
    ANNOTATION_VALUE_QUARTER,
    ANNOTATION_VALUE_WEEK,
    ANNOTATION_VALUE_YEAR,
)
from advanced_report_builder.models import ReportType, Target
from advanced_report_builder.utils import (
    count_days,
    get_report_builder_class,
    get_template_type_class,
    split_attr,
    split_slug,
)
from advanced_report_builder.variable_date import VariableDate
from advanced_report_builder.views.helpers import QueryBuilderForm
from advanced_report_builder.views.report import ReportBase
from advanced_report_builder.views.report_utils_mixin import ReportUtilsMixin
from advanced_report_builder.views.targets.utils import TargetUtils


class ChartJSTable(DatatableTable):
    def __init__(self, *args, **kwargs):
        pk = kwargs.pop('pk', None)
        self.axis_scale = kwargs.pop('axis_scale', None)
        self.targets = kwargs.pop('targets', None)
        self.raw_data = None

        super().__init__(*args, **kwargs)
        if pk:
            self.filter['pk'] = pk

    def model_table_setup(self):
        try:
            targets_data = []
            error = False
            try:
                data = self.get_table_array(self.kwargs.get('request'), self.get_query())
                self.raw_data = data
            except (DataError, FieldError):
                data = [['N/A']]
                error = True
            if self.targets is not None and not error:
                targets = self.targets.all()
                if targets and len(data) > 0:
                    targets_data = self.process_data_structure_target(targets=targets, data=data)
            return mark_safe(
                json.dumps(
                    {
                        'initsetup': json.loads(self.col_def_str()),
                        'data': data,
                        'targets': targets_data,
                        'row_titles': self.all_titles(),
                        'table_id': self.table_id,
                    }
                )
            )
        except (ProgrammingError, TypeError, ValueError, KeyError) as e:
            raise ReportError(e)

    def process_data_structure_target(self, targets, data):
        results = []
        for target in targets:
            if target.period_type == Target.PeriodType.MONTHLY:
                new_data_structure = []
                for data_dict in data:
                    target_value = self.process_target_results(data_dict=data_dict, target=target)
                    new_data_structure.append(target_value)
                label = target.name + ' Target'
                colour = '#' + target.default_colour
                results.append(
                    {
                        'label': label,
                        'data': new_data_structure,
                        'borderWidth': 1,
                        'backgroundColor': [colour for _ in range(len(new_data_structure))],
                        'borderColor': '#' + target.default_colour,
                    }
                )
        return results

    @staticmethod
    def process_target_results(data_dict, target):
        """
        Get the correct target data from from the target.
        :param data_dict:
        :param target:
        :return:
        """
        start_date = datetime.strptime(data_dict[0], '%Y-%m-%d').date()

        date_offset = DateOffset()

        # since the targets are in months, this is the value we need.
        first_day_month = start_date.replace(day=1)
        next_date = date_offset.get_offset('1m', first_day_month) - timedelta(days=1)
        target_utils = TargetUtils()

        target_value = target_utils.get_monthly_target_value_for_range(
            min_date=first_day_month,
            max_date=next_date,
            target=target,
        )

        return target_value


class ChartBaseView(ReportBase, ReportUtilsMixin, TemplateView):
    date_field = ReportBuilderDateColumn
    chart_js_table = ChartJSTable

    template_name = 'advanced_report_builder/charts/report.html'

    def __init__(self, *args, **kwargs):
        self.chart_report = None
        self.show_toolbar = False
        self.table = None
        super().__init__(*args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        self.slug = split_slug(kwargs.get('slug'))
        self.enable_edit = kwargs.get('enable_edit')
        self.dashboard_report = kwargs.get('dashboard_report')
        if self.enable_edit or (self.dashboard_report and not self.dashboard_report.top) or not self.dashboard_report:
            self.show_toolbar = True
        return super().dispatch(request, *args, **kwargs)

    def extra_filters(self, query):
        report_query = self.get_report_query(report=self.chart_report)
        option_query = self.get_report_option_query()
        if report_query or option_query:
            search_filter_data = report_query.query if report_query else None
            query = self.process_query_filters(
                query=query, search_filter_data=search_filter_data, extra_filter=option_query
            )
        return query

    def get_report_template(self):
        template_type_class = get_template_type_class()
        return template_type_class.get_template_name_from_instance_type(
            instance_type=self.report.instance_type, template_style=self.report.template_style
        )

    def get_date_format(self):
        return '%Y-%m-%d'

    def get_date_field(self, index, fields, base_model, table):
        field_name = self.chart_report.date_field
        if field_name is None:
            return None
        report_builder_class = get_report_builder_class(model=base_model, report_type=self.chart_report.report_type)

        django_field, col_type_override, _, _ = self.get_field_details(
            base_model=base_model,
            field=field_name,
            report_builder_class=report_builder_class,
            table=table,
        )

        if col_type_override:
            field_name = col_type_override.field

        date_format = self.get_date_format()

        date_function_kwargs = {'title': field_name, 'date_format': date_format}

        annotations_value = self.chart_report.axis_scale

        new_field_name = f'{annotations_value}_{field_name}_{index}'
        function = ANNOTATION_VALUE_FUNCTIONS[annotations_value]
        date_function_kwargs['annotations_value'] = {new_field_name: function(field_name)}
        field_name = new_field_name

        date_function_kwargs.update({'field': field_name, 'column_name': field_name, 'model_path': ''})

        field = self.date_field(**date_function_kwargs)
        fields.append(field)
        return field_name

    @staticmethod
    def _set_multiple_title(database_values, value_prefix, fields, text):
        results = {}
        for field in fields:
            value = database_values[value_prefix + '__' + field]
            results[field] = value
        return text.format(**results)

    def process_query_results(self, base_model, table):
        fields = []
        date_field_name = self.get_date_field(0, fields, base_model=base_model, table=table)
        if date_field_name is not None:
            table.order_by = [date_field_name]
        else:
            table.order_by = ['id']

        if not self.chart_report.fields:
            return fields
        chart_fields = self.chart_report.fields

        report_builder_class = get_report_builder_class(model=base_model, report_type=self.chart_report.report_type)

        for index, table_field in enumerate(chart_fields, 1):
            field = table_field['field']

            django_field, col_type_override, _, _ = self.get_field_details(
                base_model=base_model,
                field=field,
                report_builder_class=report_builder_class,
                table=table,
            )

            if isinstance(django_field, NUMBER_FIELDS) or (
                col_type_override is not None and col_type_override.annotations
            ):
                data_attr = split_attr(table_field)
                if data_attr.get('multiple_columns') == '1':
                    query = self.extra_filters(query=table.model.objects)

                    multiple_column_field = data_attr.get('multiple_column_field')
                    if multiple_column_field is None:
                        return
                    report_builder_class = self._get_report_builder_class(
                        base_model=base_model,
                        field_str=multiple_column_field,
                        report_builder_class=report_builder_class,
                    )
                    try:
                        _fields = report_builder_class.default_multiple_column_fields
                    except AttributeError:
                        return
                    default_multiple_column_fields = [multiple_column_field + '__' + x for x in _fields]
                    order_by = f'{multiple_column_field}__{report_builder_class.default_multiple_pk}'
                    positive_colour_field = self.get_field_path(
                        field_name=data_attr.get('positive_colour_field'),
                        base_model=base_model,
                        report_builder_class=report_builder_class,
                        table=table,
                    )
                    if positive_colour_field is not None:
                        default_multiple_column_fields.append(positive_colour_field)

                    negative_colour_field = self.get_field_path(
                        field_name=data_attr.get('negative_colour_field'),
                        base_model=base_model,
                        report_builder_class=report_builder_class,
                        table=table,
                    )
                    if negative_colour_field is not None:
                        default_multiple_column_fields.append(negative_colour_field)

                    results = (
                        query.order_by(order_by)
                        .distinct(multiple_column_field)
                        .values(multiple_column_field, *default_multiple_column_fields)
                    )
                    held_kwargs = copy.deepcopy(col_type_override.kwargs)
                    for multiple_index, result in enumerate(results):
                        col_type_override.kwargs = copy.deepcopy(held_kwargs)

                        suffix = self._set_multiple_title(
                            database_values=result,
                            value_prefix=multiple_column_field,
                            fields=_fields,
                            text=report_builder_class.default_multiple_column_text,
                        )
                        extra_filter = Q((multiple_column_field, result[multiple_column_field]))

                        additional_options = {}
                        if positive_colour_field is not None:
                            additional_options['positive_colour'] = result[positive_colour_field]

                        if negative_colour_field is not None:
                            additional_options['negative_colour'] = result[negative_colour_field]

                        self.get_number_field(
                            annotations_type=self.chart_report.axis_value_type,
                            append_annotation_query=True,
                            index=f'{index}_{multiple_index}',
                            data_attr=data_attr,
                            table_field=table_field,
                            fields=fields,
                            col_type_override=col_type_override,
                            extra_filter=extra_filter,
                            title_suffix=suffix,
                            multiple_index=multiple_index,
                            additional_options=additional_options,
                        )

                else:
                    self.get_number_field(
                        annotations_type=self.chart_report.axis_value_type,
                        append_annotation_query=False,
                        index=index,
                        data_attr=data_attr,
                        table_field=table_field,
                        fields=fields,
                        col_type_override=col_type_override,
                    )
        return fields

    def get_field_path(self, field_name, base_model, report_builder_class, table):
        if field_name:
            _, _, _, field_path = self.get_field_details(
                base_model=base_model,
                field=field_name,
                report_builder_class=report_builder_class,
                table=table,
            )
            return field_path
        return None

    # noinspection PyUnresolvedReferences
    @staticmethod
    def add_colour_offset(colour, multiple_index):
        if multiple_index > 0:
            offset = 50 * multiple_index
            colour_list = list(int(colour[i : i + 2], 16) for i in (0, 2, 4))
            _, colour_list[0] = divmod(colour_list[0] + offset, 255)
            _, colour_list[1] = divmod(colour_list[1] + offset, 255)
            _, colour_list[2] = divmod(colour_list[2] + offset, 255)
            return '{:02x}{:02x}{:02x}'.format(*colour_list)
        else:
            return colour

    def setup_table(self, base_model):
        if hasattr(self.chart_report, 'axis_scale'):
            self.table = self.chart_js_table(model=base_model, axis_scale=self.chart_report.axis_scale)
        else:
            self.table = self.chart_js_table(model=base_model)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        base_model = self.chart_report.get_base_model()
        if base_model:
            self.setup_table(base_model=base_model)
            self.table.extra_filters = self.extra_filters
            try:
                fields = self.process_query_results(base_model=base_model, table=self.table)
            except (FieldError, FieldDoesNotExist) as e:
                raise ReportError(e)
            self.table.add_columns(*fields)
            context['datatable'] = self.table
        context['show_toolbar'] = self.show_toolbar
        context['title'] = self.get_title()
        return context

    def setup_menu(self):
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
        query_id = self.slug.get(f'query{self.chart_report.id}')
        slug_str = ''
        if query_id:
            slug_str = f'-query_id-{query_id}'
        return self.edit_report_menu(
            request=self.request,
            chart_report_id=self.chart_report.id,
            slug_str=slug_str,
        )

    @staticmethod
    def edit_report_menu(request, chart_report_id, slug_str):
        return []

    def get_period_divider(
        self,
        annotation_value_choice,
        start_date_type,
        end_date_type,
        exclude_weekdays=None,
        exclude_dates=None,
    ):
        """
        Calculates the number of periods (year, quarter, month, week, day)
        between two variable dates.
        Supports working-day exclusions and financial quarters.

        financial_year_start_month:
            1 = Jan (default calendar year)
            4 = Apr (UK fiscal year)
            7 = Jul (AU fiscal year)
        """
        variable_date = VariableDate()

        financial_year_start_month = self.get_financial_month()

        start_date_and_time, _, _ = variable_date.get_variable_dates(
            range_type=start_date_type, financial_year_start_month=financial_year_start_month
        )
        _, end_date_and_time, _ = variable_date.get_variable_dates(
            range_type=end_date_type, financial_year_start_month=financial_year_start_month
        )

        start_date = start_date_and_time.date()
        end_date = end_date_and_time.date()

        # YEAR
        if annotation_value_choice == ANNOTATION_VALUE_YEAR:
            if exclude_weekdays or exclude_dates:
                total_working_days = count_days(
                    start_date,
                    end_date,
                    exclude_weekdays=exclude_weekdays,
                    exclude_dates=exclude_dates,
                )
                divider = max(1, math.ceil(total_working_days / 260))
            else:
                divider = abs(end_date.year - start_date.year) + 1

        # FINANCIAL QUARTER
        elif annotation_value_choice == ANNOTATION_VALUE_FINANCIAL_QUARTER:
            # Financial year offset (e.g. 4 → April)
            fy_offset = financial_year_start_month - 1

            # Convert actual months to financial-year-relative months (0–11)
            start_fm = (start_date.year * 12) + (start_date.month - 1) - fy_offset
            end_fm = (end_date.year * 12) + (end_date.month - 1) - fy_offset

            # Month difference (inclusive of partial months if days > 0)
            delta = relativedelta(end_date, start_date)

            # Adjust using financial-year-relative absolute month numbers
            adjusted_months = (end_fm - start_fm) + (1 if delta.days > 0 else 0)

            # Number of financial quarters (3-month blocks)
            divider = max(1, math.ceil(adjusted_months / 3))

            # If working-day exclusions apply, switch to day-based quarter calculation
            if exclude_weekdays or exclude_dates:
                total_working_days = count_days(
                    start_date,
                    end_date,
                    exclude_weekdays=exclude_weekdays,
                    exclude_dates=exclude_dates,
                )
                # Approx. 65 working days per quarter
                divider = max(1, math.ceil(total_working_days / 65))

        # CALENDAR QUARTER
        elif annotation_value_choice == ANNOTATION_VALUE_QUARTER:
            if exclude_weekdays or exclude_dates:
                total_working_days = count_days(
                    start_date,
                    end_date,
                    exclude_weekdays=exclude_weekdays,
                    exclude_dates=exclude_dates,
                )
                divider = max(1, math.ceil(total_working_days / 65))
            else:
                delta = relativedelta(end_date, start_date)
                divider = delta.years * 4 + math.ceil(delta.months / 3)
                if delta.days > 0 and delta.months % 3 == 0:
                    divider += 1
                divider = max(1, divider)
        # MONTH
        elif annotation_value_choice == ANNOTATION_VALUE_MONTH:
            rdate = relativedelta(end_date, start_date)
            divider = rdate.years * 12 + rdate.months
            if rdate.days > 0:
                divider += 1
            divider = divider or 1

        # WEEK
        elif annotation_value_choice == ANNOTATION_VALUE_WEEK:
            if exclude_weekdays or exclude_dates:
                total_working_days = count_days(
                    start_date,
                    end_date,
                    exclude_weekdays=exclude_weekdays,
                    exclude_dates=exclude_dates,
                )
                ex = {d for d in (exclude_weekdays or []) if 1 <= d <= 7}
                workdays_per_week = 7 - len(ex) if ex else 7
                if workdays_per_week == 0:
                    raise ReportError('All days are excluded from the week; cannot calculate number of weeks.')
                divider = math.ceil(total_working_days / workdays_per_week)
            else:
                monday1 = start_date - timedelta(days=start_date.weekday())
                monday2 = end_date - timedelta(days=end_date.weekday())
                divider = max(1, int((monday2 - monday1).days / 7))

        # DAY
        elif annotation_value_choice == ANNOTATION_VALUE_DAY:
            divider = count_days(
                start_date,
                end_date,
                exclude_weekdays=exclude_weekdays,
                exclude_dates=exclude_dates,
            )

        else:
            raise ReportError('unknown annotation_value_choice')

        return divider


class ChartBaseFieldForm(ReportBuilderFieldUtils, QueryBuilderForm):
    cancel_class = 'btn-secondary modal-cancel'

    def __init__(self, *args, **kwargs):
        self.django_field = None
        self.col_type_override = None
        super().__init__(*args, **kwargs)

    def cancel_button(self, css_class=cancel_class, **kwargs):
        commands = [{'function': 'close'}]
        return self.button('Cancel', commands, css_class, **kwargs)

    def get_report_type_details(self):
        data = json.loads(base64.b64decode(self.slug['data']))

        report_type = get_object_or_404(ReportType, pk=self.slug['report_type_id'])
        base_model = report_type.content_type.model_class()

        report_builder_class = get_report_builder_class(model=base_model, report_type=report_type)

        self.django_field, self.col_type_override, _, _ = self.get_field_details(
            base_model=base_model,
            field=data['field'],
            report_builder_class=report_builder_class,
        )

        return report_type, base_model

    def _get_query_builder_foreign_key_fields(
        self,
        base_model,
        report_builder_class,
        fields,
        prefix='',
        title_prefix='',
        previous_base_model=None,
    ):
        for include_field, include in report_builder_class.includes.items():
            app_label, model, report_builder_fields_str = include['model'].split('.')
            new_model = apps.get_model(app_label, model)
            if new_model != previous_base_model:
                new_report_builder_class = get_report_builder_class(
                    model=new_model, class_name=report_builder_fields_str
                )

                fields.append((prefix + include_field, title_prefix + include['title']))
                self._get_query_builder_foreign_key_fields(
                    base_model=new_model,
                    report_builder_class=new_report_builder_class,
                    fields=fields,
                    prefix=f'{prefix}{include_field}__',
                    title_prefix=f'{title_prefix}{include["title"]} --> ',
                    previous_base_model=base_model,
                )

    def setup_colour_field(self, form_fields, base_model, report_builder_class, name, data_attr, label=None):
        colour_fields = []
        self._get_colour_fields(
            base_model=base_model,
            report_builder_class=report_builder_class,
            fields=colour_fields,
        )
        dropdown_colour_fields = [['', '----']]
        for colour_field in colour_fields:
            dropdown_colour_fields.append([colour_field['id'], colour_field['text']])

        form_fields[name] = ChoiceField(
            choices=dropdown_colour_fields,
            required=False,
            widget=Select2(),
            label=label,
        )
        if name in data_attr:
            form_fields[name].initial = data_attr.get(name)
