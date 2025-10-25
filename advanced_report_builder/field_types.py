from dataclasses import dataclass
from typing import Optional

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
    django_field: Optional[models.Field] = None
    column: Optional[str] = None
    prefix: Optional[str] = None
    full_field_name: Optional[str] = None
    column_id: Optional[int] = None

    def to_dict(self):
        return self.__dict__

class FieldTypes(ReportBuilderFieldUtils):
    FIELD_TYPE_STRING = 1
    FIELD_TYPE_NUMBER = 2
    FIELD_TYPE_DATE = 3
    FIELD_TYPE_BOOLEAN = 4
    FIELD_TYPE_MULTIPLE_CHOICE = 5
    FIELD_TYPE_FOREIGN_KEY = 6
    FIELD_TYPE_ABSTRACT_USER = 7
    FIELD_TYPE_PART_DATE = 8

    def get_operator(self, field_type):
        operators = {
            self.FIELD_TYPE_STRING: [
                'equal',
                'not_equal',
                'contains',
                'not_contains',
                'begins_with',
                'not_begins_with',
                'ends_with',
                'not_ends_with',
            ],
            self.FIELD_TYPE_NUMBER: [
                'equal',
                'not_equal',
                'less',
                'less_or_equal',
                'greater',
                'greater_or_equal',
            ],
            self.FIELD_TYPE_DATE: [
                'equal',
                'not_equal',
                'less',
                'less_or_equal',
                'greater',
                'greater_or_equal',
                'is_null',
                'is_not_null',
            ],
            self.FIELD_TYPE_PART_DATE: ['equal', 'not_equal', 'is_null', 'is_not_null'],
            self.FIELD_TYPE_BOOLEAN: ['equal', 'not_equal'],
            self.FIELD_TYPE_MULTIPLE_CHOICE: ['in', 'not_in'],
            self.FIELD_TYPE_FOREIGN_KEY: ['is_null', 'is_not_null'],
            self.FIELD_TYPE_ABSTRACT_USER: ['equal', 'not_equal'],
        }
        return operators.get(field_type)


    def get_filters(self, fields, query_builder_filters):
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
                        'operators': self.get_operator(self.FIELD_TYPE_MULTIPLE_CHOICE),
                    }
                )
            elif field_type == FieldType.STRING:
                query_builder_filters.append(
                    {
                        'id': field_detail.column_id,
                        'label': field_detail.title,
                        'field': field_detail.full_field_name,
                        'type': 'string',
                        'operators': self.get_operator(self.FIELD_TYPE_STRING),
                        'validation': {'allow_empty_value': True},
                    }
                )
            elif field_type == FieldType.INTEGER:
                if field_detail.django_field.choices is None:
                    query_builder_filter = {
                        'id': field_detail.column_id,
                        'label': field_detail.title,
                        'field': field_detail.full_field_name,
                        'type': 'integer',
                        'operators': self.get_operator(self.FIELD_TYPE_NUMBER),
                    }
                else:
                    query_builder_filter = {
                        'id': field_detail.column_id,
                        'label': field_detail.title,
                        'field': field_detail.full_field_name,
                        'type': 'integer',
                        'input': 'select',
                        'multiple': True,
                        'values': dict(field_detail.django_field.choices),
                        'operators': self.get_operator(self.FIELD_TYPE_MULTIPLE_CHOICE),
                    }
                query_builder_filters.append(query_builder_filter)
            elif field_type == FieldType.BOOLEAN:
                query_builder_filters.append(
                    {
                        'id': field_detail.column_id,
                        'label': field_detail.title,
                        'field': field_detail.full_field_name,
                        'input': 'select',
                        'operators': self.get_operator(self.FIELD_TYPE_BOOLEAN),
                        'values': {'0': 'False', '1': 'True'},
                    }
                )
            elif field_type == FieldType.DATE:
                self.get_date_field(
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
                    'operators': self.get_operator(self.FIELD_TYPE_MULTIPLE_CHOICE),
                }
                query_builder_filters.append(query_builder_filter)

    def get_foreign_key_null_field(self, query_builder_filters, field, title):
        query_builder_filters.append(
            {
                'id': field,
                'label': title,
                'field': field,
                'type': 'integer',
                'operators': self.get_operator(self.FIELD_TYPE_FOREIGN_KEY),
                'validation': {'allow_empty_value': True},
            }
        )

    def get_date_field(self, column_id, query_builder_filters, field, title):
        variable_date = VariableDate()
        query_builder_filter = {
            'id': f'{column_id}__variable_date',
            'label': f'{title} (Variable)',
            'field': field,
            'operators': self.get_operator(self.FIELD_TYPE_DATE),
            'input': 'select',
            'values': variable_date.get_variable_date_filter_values(),
        }
        query_builder_filters.append(query_builder_filter)
        query_builder_filter = {
            'id': f'{column_id}__variable_year',
            'label': f'{title} (Year)',
            'field': field,
            'operators': self.get_operator(self.FIELD_TYPE_DATE),
            'input': 'select',
            'values': variable_date.get_date_filter_years(),
        }
        query_builder_filters.append(query_builder_filter)
        query_builder_filter = {
            'id': f'{column_id}__variable_month',
            'label': f'{title} (Month)',
            'field': field,
            'operators': self.get_operator(self.FIELD_TYPE_DATE),
            'input': 'select',
            'values': variable_date.get_date_filter_months(),
        }
        query_builder_filters.append(query_builder_filter)

        query_builder_filter = {
            'id': f'{column_id}__variable_quarter',
            'label': f'{title} (Quarter)',
            'field': field,
            'operators': self.get_operator(self.FIELD_TYPE_PART_DATE),
            'input': 'select',
            'values': variable_date.get_date_filter_quarters(),
        }
        query_builder_filters.append(query_builder_filter)

    def get_abstract_user_field(self, query_builder_filters, field, title):
        query_builder_filters.append(
            {
                'id': f'{field}__logged_in_user',
                'label': f'{title} (Logged in user)',
                'field': field,
                'input': 'select',
                'operators': self.get_operator(self.FIELD_TYPE_ABSTRACT_USER),
                'values': {'0': 'False', '1': 'True'},
            }
        )

    def get_field_types(self,
                        field_results,
                        base_model,
                        report_builder_class,
                        prefix='',
                        title_prefix='',
                        previous_base_model=None,
                        show_includes=True
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
                                models.IntegerField | models.PositiveSmallIntegerField | models.PositiveIntegerField,
                        ):
                            selected_field_type = FieldType.INTEGER
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
                        field_results.append(FieldDetail(django_field=django_field,
                                                         column=column,
                                                         title=title_prefix + column.title,
                                                         field=column.column_name,
                                                         prefix=prefix,
                                                         field_type=selected_field_type,
                                                         full_field_name=full_field_name,
                                                         column_id=column_id))

        if show_includes:
            for include_field, include in report_builder_class.includes.items():
                app_label, model, report_builder_fields_str = include['model'].split('.')
                new_model = apps.get_model(app_label, model)
                new_report_builder_class = get_report_builder_class(model=new_model,
                                                                    class_name=report_builder_fields_str)

                if new_model != previous_base_model:
                    _foreign_key = getattr(base_model, include_field, None)

                    add_null_field = _foreign_key.field.null if hasattr(_foreign_key, 'field') else True

                    if add_null_field:
                        field_results.append(FieldDetail(field=prefix + include_field,
                                                         title=title_prefix + include['title'],
                                                         field_type=FieldType.NULL_FIELD))
                    if isinstance(new_model(), AbstractUser):
                        field_results.append(FieldDetail(field=prefix + include_field,
                                                         title=title_prefix + include['title'],
                                                         field_type=FieldType.ABSTRACT_USER))
                    self.get_field_types(
                        field_results=field_results,
                        base_model=new_model,
                        report_builder_class=new_report_builder_class,
                        prefix=f'{prefix}{include_field}__',
                        title_prefix=f'{include["title"]} --> ',
                        previous_base_model=base_model,
                        show_includes=include.get('show_includes', True),
                    )