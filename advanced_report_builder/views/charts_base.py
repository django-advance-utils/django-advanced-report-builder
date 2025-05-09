import base64
import json
from datetime import datetime, timedelta

from date_offset.date_offset import DateOffset
from dateutil.relativedelta import relativedelta
from django.apps import apps
from django.core.exceptions import FieldError
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
    ANNOTATION_VALUE_FUNCTIONS,
    ANNOTATION_VALUE_MONTH,
    ANNOTATION_VALUE_QUARTER,
    ANNOTATION_VALUE_WEEK,
    ANNOTATION_VALUE_YEAR,
)
from advanced_report_builder.models import ReportType
from advanced_report_builder.utils import (
    get_report_builder_class,
    split_attr,
    split_slug,
)
from advanced_report_builder.variable_date import VariableDate
from advanced_report_builder.views.helpers import QueryBuilderForm
from advanced_report_builder.views.report import ReportBase
from advanced_report_builder.views.report_utils_mixin import ReportUtilsMixin
from advanced_report_builder.views.targets.utils import get_target_value


class ChartJSTable(DatatableTable):
    def __init__(self, *args, **kwargs):
        pk = kwargs.pop('pk', None)
        self.axis_scale = kwargs.pop('axis_scale', None)
        self.targets = kwargs.pop('targets', None)
        super().__init__(*args, **kwargs)
        if pk:
            self.filter['pk'] = pk

    def model_table_setup(self):
        try:
            targets = []
            try:
                data = self.get_table_array(self.kwargs.get('request'), self.get_query())
            except (DataError, FieldError):
                data = [['N/A']]
            if self.targets is not None:
                targets = self.targets.all()
                if targets and len(data) > 0:
                    targets = self.process_data_structure_target(targets=targets, data=data)
            return mark_safe(
                json.dumps(
                    {
                        'initsetup': json.loads(self.col_def_str()),
                        'data': data,
                        'targets': targets,
                        'row_titles': self.all_titles(),
                        'table_id': self.table_id,
                    }
                )
            )
        except ProgrammingError as e:
            raise ReportError(e)

    def process_data_structure_target(self, targets, data):
        results = []
        for target in targets:
            new_data_structure = []
            for data_dict in data:
                target_value = self.process_target_results(data_dict=data_dict, target=target)
                new_data_structure.append(target_value)
            label = target.name + ' Target'
            colour = '#' + target.colour
            results.append(
                {
                    'label': label,
                    'data': new_data_structure,
                    'borderWidth': 1,
                    'backgroundColor': [colour for _ in range(len(new_data_structure))],
                    'borderColor': '#' + target.colour,
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

        target_value = get_target_value(
            min_date=first_day_month,
            max_date=next_date,
            target=target,
            month_range=True,
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
        if report_query:
            query = self.process_query_filters(query=query, search_filter_data=report_query.query)
        return query

    def get_date_format(self):
        return '%Y-%m-%d'

    def get_date_field(self, index, fields, base_model, table):
        field_name = self.chart_report.date_field
        if field_name is None:
            return
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

                    for multiple_index, result in enumerate(results):
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
                            append_annotation_query=False,
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

        self.setup_table(base_model=base_model)
        self.table.extra_filters = self.extra_filters
        fields = self.process_query_results(base_model=base_model, table=self.table)
        self.table.add_columns(*fields)

        context['show_toolbar'] = self.show_toolbar
        context['datatable'] = self.table
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

    @staticmethod
    def get_period_divider(annotation_value_choice, start_date_type, end_date_type):
        variable_date = VariableDate()
        start_date_and_time, _, _ = variable_date.get_variable_dates(start_date_type)
        _, end_date_and_time, _ = variable_date.get_variable_dates(end_date_type)
        if annotation_value_choice == ANNOTATION_VALUE_YEAR:
            divider = abs(end_date_and_time.year - start_date_and_time.year) + 1
        elif annotation_value_choice == ANNOTATION_VALUE_QUARTER:
            delta = relativedelta(end_date_and_time, start_date_and_time)
            divider = delta.years * 4 + delta.months // 3
        elif annotation_value_choice == ANNOTATION_VALUE_MONTH:
            rdate = relativedelta(end_date_and_time, start_date_and_time)
            divider = 0
            if rdate.years is not None and abs(rdate.years) > 0:
                divider += abs(rdate.years) * 12
            if rdate.months is not None and abs(rdate.months) > 0:
                divider += rdate.months
            if rdate.days is not None and abs(rdate.days) > 0:
                divider += 1
        elif annotation_value_choice == ANNOTATION_VALUE_WEEK:
            monday1 = start_date_and_time - timedelta(days=start_date_and_time.weekday())
            monday2 = end_date_and_time - timedelta(days=end_date_and_time.weekday())
            divider = int((monday2 - monday1).days / 7)
        elif annotation_value_choice == ANNOTATION_VALUE_DAY:
            divider = (end_date_and_time - start_date_and_time).days
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
