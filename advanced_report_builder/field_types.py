from dataclasses import dataclass
from enum import Enum

from django.apps import apps
from django.contrib.auth.models import AbstractUser
from django.db import models
from django_datatables.columns import ManyToManyColumn

from advanced_report_builder.column_types import DATE_FIELDS
from advanced_report_builder.columns import FilterForeignKeyColumn
from advanced_report_builder.field_utils import ReportBuilderFieldUtils
from advanced_report_builder.globals import FieldType
from advanced_report_builder.utils import get_report_builder_class
from advanced_report_builder.variable_date import VariableDate


@dataclass(slots=True)
class FieldDetail:
    field_type: FieldType
    field: str
    title: str
    django_field: models.Field | None = None
    column: str | None = None
    prefix: str | None = None
    full_field_name: str | None = None
    column_id: int | None = None

    def to_dict(self):
        return self.__dict__


class FieldTypes(ReportBuilderFieldUtils):
    class OperatorFieldType(Enum):
        STRING = 1
        NUMBER = 2
        DATE = 3
        BOOLEAN = 4
        MULTIPLE_CHOICE = 5
        FOREIGN_KEY = 6
        ABSTRACT_USER = 7
        PART_DATE = 8

        COMPARE_STRING = 9
        COMPARE_NUMBER = 10
        COMPARE_DATE = 11
        COMPARE_BOOLEAN = 12
        WEEKDAYS = 13
        WEEK_NUMBER = 14
        FINANCIAL_WEEK_NUMBER = 15

    def get_operator(self, field_type):
        operators = {
            self.OperatorFieldType.STRING: [
                'equal',
                'not_equal',
                'contains',
                'not_contains',
                'begins_with',
                'not_begins_with',
                'ends_with',
                'not_ends_with',
            ],
            self.OperatorFieldType.NUMBER: [
                'equal',
                'not_equal',
                'less',
                'less_or_equal',
                'greater',
                'greater_or_equal',
            ],
            self.OperatorFieldType.DATE: [
                'equal',
                'not_equal',
                'less',
                'less_or_equal',
                'greater',
                'greater_or_equal',
                'is_null',
                'is_not_null',
            ],
            self.OperatorFieldType.PART_DATE: ['equal', 'not_equal', 'is_null', 'is_not_null'],
            self.OperatorFieldType.BOOLEAN: ['equal', 'not_equal'],
            self.OperatorFieldType.MULTIPLE_CHOICE: ['in', 'not_in'],
            self.OperatorFieldType.FOREIGN_KEY: ['is_null', 'is_not_null'],
            self.OperatorFieldType.ABSTRACT_USER: ['equal', 'not_equal'],
            self.OperatorFieldType.WEEKDAYS: ['equal', 'not_equal'],
            self.OperatorFieldType.WEEK_NUMBER: [
                'equal',
                'not_equal',
                'less',
                'less_or_equal',
                'greater',
                'greater_or_equal',
            ],
            self.OperatorFieldType.FINANCIAL_WEEK_NUMBER: [
                'equal',
                'not_equal',
                'less',
                'less_or_equal',
                'greater',
                'greater_or_equal',
            ],
            self.OperatorFieldType.COMPARE_STRING: ['equal', 'not_equal'],
            self.OperatorFieldType.COMPARE_NUMBER: [
                'equal',
                'not_equal',
                'less',
                'less_or_equal',
                'greater',
                'greater_or_equal',
            ],
            self.OperatorFieldType.COMPARE_DATE: [
                'equal',
                'not_equal',
                'less',
                'less_or_equal',
                'greater',
                'greater_or_equal',
            ],
            self.OperatorFieldType.COMPARE_BOOLEAN: ['equal', 'not_equal'],
        }
        return operators.get(field_type)

    def get_filters(self, fields, query_builder_filters, field_results_types):
        for field_detail in fields:
            field_type = field_detail.field_type

            if field_type == FieldType.NULL_FIELD:
                self.get_foreign_key_null_field(
                    query_builder_filters=query_builder_filters,
                    field=field_detail.field,
                    title=field_detail.title,
                )

            elif field_type == FieldType.ABSTRACT_USER:
                self.get_abstract_user_field(
                    query_builder_filters=query_builder_filters,
                    field=field_detail.field,
                    title=field_detail.title,
                )

            elif field_type == FieldType.FILTER_FOREIGN_KEY:
                query_builder_filters.append(
                    {
                        'id': field_detail.column_id,
                        'label': field_detail.title,
                        'field': field_detail.full_field_name,
                        'type': 'string',
                        'input': 'select',
                        'multiple': True,
                        'values': field_detail.column.get_query_options(),
                        'operators': self.get_operator(self.OperatorFieldType.MULTIPLE_CHOICE),
                    }
                )
            elif field_type == FieldType.STRING:
                query_builder_filters.append(
                    {
                        'id': field_detail.column_id,
                        'label': f'{field_detail.title} (Field vs Value)',
                        'field': field_detail.full_field_name,
                        'type': 'string',
                        'operators': self.get_operator(self.OperatorFieldType.STRING),
                        'validation': {'allow_empty_value': True},
                    }
                )
                query_builder_filters.append(
                    {
                        'id': f'{field_detail.column_id}__field_vs_field',
                        'label': f'{field_detail.title} (Field vs Field)',
                        'field': field_detail.full_field_name,
                        'input': 'select',
                        'operators': self.get_operator(self.OperatorFieldType.COMPARE_STRING),
                        'values': field_results_types[FieldType.STRING],
                    }
                )
            elif field_type == FieldType.NUMBER:
                if field_detail.django_field.choices is None:
                    query_builder_filter = {
                        'id': field_detail.column_id,
                        'label': f'{field_detail.title} (Field vs Value)',
                        'field': field_detail.full_field_name,
                        'type': 'integer',
                        'operators': self.get_operator(self.OperatorFieldType.NUMBER),
                    }
                    query_builder_filters.append(
                        {
                            'id': f'{field_detail.column_id}__field_vs_field',
                            'label': f'{field_detail.title} (Field vs Field)',
                            'field': field_detail.full_field_name,
                            'input': 'select',
                            'operators': self.get_operator(self.OperatorFieldType.COMPARE_NUMBER),
                            'values': field_results_types[FieldType.NUMBER],
                        }
                    )
                else:
                    query_builder_filter = {
                        'id': field_detail.column_id,
                        'label': field_detail.title,
                        'field': field_detail.full_field_name,
                        'type': 'integer',
                        'input': 'select',
                        'multiple': True,
                        'values': dict(field_detail.django_field.choices),
                        'operators': self.get_operator(self.OperatorFieldType.MULTIPLE_CHOICE),
                    }
                query_builder_filters.append(query_builder_filter)
            elif field_type == FieldType.BOOLEAN:
                query_builder_filters.append(
                    {
                        'id': field_detail.column_id,
                        'label': f'{field_detail.title} (Field vs Value)',
                        'field': field_detail.full_field_name,
                        'input': 'select',
                        'operators': self.get_operator(self.OperatorFieldType.BOOLEAN),
                        'values': {'0': 'False', '1': 'True'},
                    }
                )
                query_builder_filters.append(
                    {
                        'id': f'{field_detail.column_id}__field_vs_field',
                        'label': f'{field_detail.title} (Field vs Field)',
                        'field': field_detail.full_field_name,
                        'input': 'select',
                        'operators': self.get_operator(self.OperatorFieldType.COMPARE_BOOLEAN),
                        'values': field_results_types[FieldType.BOOLEAN],
                    }
                )

            elif field_type == FieldType.DATE:
                self.get_date_field(
                    field_results_types=field_results_types,
                    column_id=field_detail.column_id,
                    query_builder_filters=query_builder_filters,
                    field=field_detail.full_field_name,
                    title=field_detail.title,
                )
            elif field_type == FieldType.MANY_TO_MANY:
                choices = dict(field_detail.column.options['lookup'])
                query_builder_filter = {
                    'id': field_detail.column_id,
                    'label': field_detail.title,
                    'field': field_detail.prefix + field_detail.column.field_id,
                    'type': 'integer',
                    'input': 'select',
                    'multiple': True,
                    'values': choices,
                    'operators': self.get_operator(self.OperatorFieldType.MULTIPLE_CHOICE),
                }
                query_builder_filters.append(query_builder_filter)

    def get_foreign_key_null_field(self, query_builder_filters, field, title):
        query_builder_filters.append(
            {
                'id': field,
                'label': title,
                'field': field,
                'type': 'integer',
                'operators': self.get_operator(self.OperatorFieldType.FOREIGN_KEY),
                'validation': {'allow_empty_value': True},
            }
        )

    def get_date_field(self, field_results_types, column_id, query_builder_filters, field, title):
        variable_date = VariableDate()

        def add_filter(*, suffix, label, operator_type, values, input_type='select'):
            query_builder_filters.append(
                {
                    'id': f'{column_id}__{suffix}',
                    'label': f'{title} ({label})',
                    'field': field,
                    'operators': self.get_operator(operator_type),
                    'input': input_type,
                    'values': values,
                }
            )

        # Variable / date-part filters
        add_filter(
            suffix='variable_date',
            label='Variable',
            operator_type=self.OperatorFieldType.DATE,
            values=variable_date.get_variable_date_filter_values(),
        )

        add_filter(
            suffix='variable_year',
            label='Year',
            operator_type=self.OperatorFieldType.DATE,
            values=variable_date.get_date_filter_years(),
        )
        add_filter(
            suffix='financial_variable_year',
            label='Financial Year',
            operator_type=self.OperatorFieldType.DATE,
            values=variable_date.get_date_filter_years(),
        )
        add_filter(
            suffix='variable_month',
            label='Month',
            operator_type=self.OperatorFieldType.DATE,
            values=variable_date.get_date_filter_months(),
        )

        add_filter(
            suffix='variable_quarter',
            label='Quarter',
            operator_type=self.OperatorFieldType.PART_DATE,
            values=variable_date.get_date_filter_quarters(),
        )

        add_filter(
            suffix='variable_day',
            label='Day',
            operator_type=self.OperatorFieldType.WEEKDAYS,
            values={
                1: 'Sunday',
                2: 'Monday',
                3: 'Tuesday',
                4: 'Wednesday',
                5: 'Thursday',
                6: 'Friday',
                7: 'Saturday',
            },
        )

        # Week number (ISO-safe: 1–53)
        add_filter(
            suffix='week_number',
            label='Week Number',
            operator_type=self.OperatorFieldType.WEEK_NUMBER,
            values={i: i for i in range(1, 54)},
        )
        # Financial Week Number (1–53 relative to financial year start)
        add_filter(
            suffix='financial_week_number',
            label='Financial Week Number – requires Financial Year',
            operator_type=self.OperatorFieldType.FINANCIAL_WEEK_NUMBER,
            values={i: i for i in range(1, 54)},
        )
        # Field vs Field comparison (intentionally separate)
        query_builder_filters.append(
            {
                'id': f'{column_id}__field_vs_field',
                'label': f'{title} (Field vs Field)',
                'field': field,
                'input': 'select',
                'operators': self.get_operator(self.OperatorFieldType.COMPARE_DATE),
                'values': field_results_types[FieldType.DATE],
            }
        )

    def get_abstract_user_field(self, query_builder_filters, field, title):
        query_builder_filters.append(
            {
                'id': f'{field}__logged_in_user',
                'label': f'{title} (Logged in user)',
                'field': field,
                'input': 'select',
                'operators': self.get_operator(self.OperatorFieldType.ABSTRACT_USER),
                'values': {'0': 'False', '1': 'True'},
            }
        )

    def get_field_types(
        self,
        field_results,
        field_results_types,
        base_model,
        report_builder_class,
        prefix='',
        title_prefix='',
        previous_base_model=None,
        show_includes=True,
    ):
        for report_builder_field in report_builder_class.fields:
            if (
                not isinstance(report_builder_field, str)
                or report_builder_field not in report_builder_class.exclude_search_fields
            ):
                django_field, _, columns, _ = self.get_field_details(
                    base_model=base_model,
                    field=report_builder_field,
                    report_builder_class=report_builder_class,
                )

                for column in columns:
                    field = prefix + column.column_name
                    selected_field_type = None
                    if django_field is not None and not isinstance(column, ManyToManyColumn):
                        if isinstance(column, FilterForeignKeyColumn):
                            selected_field_type = FieldType.FILTER_FOREIGN_KEY
                        elif isinstance(django_field, models.CharField | models.TextField | models.EmailField):
                            selected_field_type = FieldType.STRING
                        elif isinstance(
                            django_field,
                            models.IntegerField
                            | models.PositiveSmallIntegerField
                            | models.PositiveIntegerField
                            | models.FloatField,
                        ):
                            selected_field_type = FieldType.NUMBER
                        elif isinstance(django_field, models.BooleanField):
                            selected_field_type = FieldType.BOOLEAN
                        elif isinstance(django_field, DATE_FIELDS):
                            selected_field_type = FieldType.DATE
                    elif isinstance(column, ManyToManyColumn):
                        selected_field_type = FieldType.MANY_TO_MANY

                    if isinstance(column.field, list):
                        full_field_name = prefix + column.field[0]
                    elif column.field is not None:
                        full_field_name = prefix + column.field
                    else:
                        full_field_name = prefix + field
                    column_id = prefix + field

                    if selected_field_type is not None:
                        title = title_prefix + column.title
                        field_results_types[selected_field_type][column_id] = title
                        field_results.append(
                            FieldDetail(
                                django_field=django_field,
                                column=column,
                                title=title,
                                field=column.column_name,
                                prefix=prefix,
                                field_type=selected_field_type,
                                full_field_name=full_field_name,
                                column_id=column_id,
                            )
                        )

        if show_includes:
            for include_field, include in report_builder_class.includes.items():
                app_label, model, report_builder_fields_str = include['model'].split('.')
                new_model = apps.get_model(app_label, model)
                new_report_builder_class = get_report_builder_class(
                    model=new_model, class_name=report_builder_fields_str
                )

                if new_model != previous_base_model:
                    _foreign_key = getattr(base_model, include_field, None)

                    add_null_field = _foreign_key.field.null if hasattr(_foreign_key, 'field') else True

                    if add_null_field:
                        field = prefix + include_field
                        title = title_prefix + include['title']
                        field_results_types[FieldType.NULL_FIELD][field] = title
                        field_results.append(FieldDetail(field=field, title=title, field_type=FieldType.NULL_FIELD))
                    if issubclass(new_model, AbstractUser):
                        field = prefix + include_field
                        title = title_prefix + include['title']
                        field_results_types[FieldType.NULL_FIELD][field] = title
                        field_results.append(FieldDetail(field=field, title=title, field_type=FieldType.ABSTRACT_USER))
                    self.get_field_types(
                        field_results=field_results,
                        field_results_types=field_results_types,
                        base_model=new_model,
                        report_builder_class=new_report_builder_class,
                        prefix=f'{prefix}{include_field}__',
                        title_prefix=f'{include["title"]} --> ',
                        previous_base_model=base_model,
                        show_includes=include.get('show_includes', True),
                    )
