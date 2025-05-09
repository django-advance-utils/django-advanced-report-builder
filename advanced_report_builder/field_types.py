from django.db import models
from django_datatables.columns import ManyToManyColumn

from advanced_report_builder.column_types import DATE_FIELDS
from advanced_report_builder.columns import FilterForeignKeyColumn
from advanced_report_builder.variable_date import VariableDate


class FieldTypes:
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

    def get_filter(self, query_builder_filters, django_field, field, title, column, prefix):
        if isinstance(column.field, list):
            full_field_name = prefix + column.field[0]
        elif column.field is not None:
            full_field_name = prefix + column.field
        else:
            full_field_name = prefix + field
        column_id = prefix + field
        if django_field is not None and not isinstance(column, ManyToManyColumn):
            if isinstance(column, FilterForeignKeyColumn):
                query_builder_filters.append(
                    {
                        'id': column_id,
                        'label': title,
                        'field': full_field_name,
                        'type': 'string',
                        'input': 'select',
                        'multiple': True,
                        'values': column.get_query_options(),
                        'operators': self.get_operator(self.FIELD_TYPE_MULTIPLE_CHOICE),
                    }
                )
            elif isinstance(django_field, models.CharField | models.TextField | models.EmailField):
                query_builder_filters.append(
                    {
                        'id': column_id,
                        'label': title,
                        'field': full_field_name,
                        'type': 'string',
                        'operators': self.get_operator(self.FIELD_TYPE_STRING),
                        'validation': {'allow_empty_value': True},
                    }
                )
            elif isinstance(
                django_field,
                models.IntegerField | models.PositiveSmallIntegerField | models.PositiveIntegerField,
            ):
                if django_field.choices is None:
                    query_builder_filter = {
                        'id': column_id,
                        'label': title,
                        'field': full_field_name,
                        'type': 'integer',
                        'operators': self.get_operator(self.FIELD_TYPE_NUMBER),
                    }
                else:
                    query_builder_filter = {
                        'id': column_id,
                        'label': title,
                        'field': full_field_name,
                        'type': 'integer',
                        'input': 'select',
                        'multiple': True,
                        'values': dict(django_field.choices),
                        'operators': self.get_operator(self.FIELD_TYPE_MULTIPLE_CHOICE),
                    }
                query_builder_filters.append(query_builder_filter)
            elif isinstance(django_field, models.BooleanField):
                query_builder_filters.append(
                    {
                        'id': column_id,
                        'label': title,
                        'field': full_field_name,
                        'input': 'select',
                        'operators': self.get_operator(self.FIELD_TYPE_BOOLEAN),
                        'values': {'0': 'False', '1': 'True'},
                    }
                )
            elif isinstance(django_field, DATE_FIELDS):
                self.get_date_field(
                    column_id=column_id,
                    query_builder_filters=query_builder_filters,
                    field=full_field_name,
                    title=title,
                )
        elif isinstance(column, ManyToManyColumn):
            choices = dict(column.options['lookup'])
            query_builder_filter = {
                'id': column_id,
                'label': title,
                'field': prefix + column.field_id,
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
