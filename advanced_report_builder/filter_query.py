import json
import operator
from functools import reduce

from django.apps import apps
from django.db.models import Q
from django.shortcuts import get_object_or_404

from advanced_report_builder.models import ReportQuery
from advanced_report_builder.variable_date import VariableDate


class FilterQueryMixin:

    def __init__(self, *args, **kwargs):
        self.table_report = None
        self.report = None
        self.dashboard_report = None
        self.enable_edit = None
        self.slug = None
        self.base_model = None
        super().__init__(*args, **kwargs)

    def process_query_filters(self, query, search_filter_data):
        result = self.process_filters(search_filter_data=search_filter_data)
        if result:
            return query.filter(result)
        return query

    def process_filters(self, search_filter_data, extra_filter=None):
        if not search_filter_data:
            return []

        query_list = self._process_group(query_data=search_filter_data)
        if extra_filter:
            query_list.append(extra_filter)

        reduce_by = self._format_group_conditions(search_filter_data['condition'])

        if query_list:
            return reduce(reduce_by, query_list)
        return []

    @staticmethod
    def _get_operator(display_operator):
        """
        Converts the display operators into operators for the Q object.
        :param display_operator:
        :return:
        """

        operators_dict = {
            'equal': '',
            'not_equal': '',  # Not equals is now done by inverting the individual Q object. (for dates).
            'less': '__lt',
            'less_or_equal': '__lte',
            'greater': '__gt',
            'greater_or_equal': '__gte',
            'contains': '__icontains',
            'not_contains': '__icontains',
            'begins_with': '__istartswith',
            'not_begins_with': '__istartswith',
            'ends_with': '__iendswith',
            'not_ends_with': '__iendswith',
            'in': '__in',
            'not_in': '__in',
            'is_null': '__isnull',
            'is_not_null': '__isnull',
        }

        query_operator = operators_dict.get(display_operator)
        return query_operator

    @staticmethod
    def _format_group_conditions(display_condition):
        """
        Converts the display condition from the javascript into a condition for the Q object.
        :param display_condition:
        :return:
        """
        if display_condition == 'AND':
            reduce_by = operator.and_
        else:
            reduce_by = operator.or_

        return reduce_by

    def _process_group(self, query_data):
        query_list = []

        for rule in query_data['rules']:
            if condition := rule.get('condition'):
                reduce_by = self._format_group_conditions(condition)
                sub_query_list = self._process_group(query_data=rule)
                if sub_query_list:
                    query_list.append(reduce(reduce_by, sub_query_list))
                continue

            field = rule['field']
            _id = rule['id']
            display_operator = rule['operator']
            query_string = field + self._get_operator(display_operator)
            data_type = rule['type']
            value = rule.get('value', '')
            if display_operator == 'is_null':
                value = True
            elif display_operator == 'is_not_null':
                value = False

            if data_type == "string" and _id.endswith('__variable_date'):
                self.get_variable_date(value=value,
                                       query_list=query_list,
                                       display_operator=display_operator,
                                       field=field,
                                       query_string=query_string)
            else:
                # 'Normal' Query.
                if display_operator in ["not_equal", "not_in", "not_contains", 'not_begins_with', "not_ends_with"]:
                    query_list.append(~Q((query_string, value)))
                else:
                    query_list.append(Q((query_string, value)))

            # elif data_type == 'date':
            #     value = datetime.strptime(value, self.date_format).date()
            # elif data_type == 'datetime':
            #     value = datetime.strptime(value, self.date_time_format)
            # elif data_type == 'integer' and value == '#current_user#':
            #     value = self.user_profile_id

            variable_date = False
        return query_list

    @staticmethod
    def get_variable_date(value, query_list, display_operator, field, query_string):
        _, range_type = value.split(":")
        variable_date = VariableDate()
        value = variable_date.get_variable_dates(range_type=int(range_type))
        if display_operator in ['less', 'greater_or_equal']:
            query_list.append(Q((query_string, value[0])))
        elif display_operator in ['greater', 'less_or_equal']:
            query_list.append(Q((query_string, value[1])))
        elif display_operator in ["not_equal", "not_in"]:
            query_list.append(~((Q((field + "__gte", value[0]))) & (Q((field + "__lte", value[1])))))
        else:
            query_list.append(((Q((field + "__gte", value[0]))) & (Q((field + "__lte", value[1])))))

    def get_report_query(self, report):

        slug_key = self.slug.get(f'query{report.pk}')
        if slug_key:
            report_query = get_object_or_404(ReportQuery, id=slug_key)
            if report_query.report_id != report.pk:
                return None
        else:
            report_query = report.reportquery_set.first()
        return report_query

    def get_title(self):
        if self.dashboard_report and self.dashboard_report.name_override:
            return self.dashboard_report.name_override
        else:
            return self.report.name

    def _get_report_builder_class(self, base_model, field_str, report_builder_class, previous_base_model=None):
        if '__' in field_str:
            field_parts = field_str.split('__')
            include_str = field_parts[0]
            new_field_str = '__'.join(field_parts[1:])

            for include in report_builder_class.includes:
                app_label, model, report_builder_fields_str = include['model'].split('.')
                new_model = apps.get_model(app_label, model)
                new_report_builder_fields = getattr(new_model, report_builder_fields_str, None)

                if new_model != previous_base_model and include_str == include['field']:
                    result = self._get_report_builder_class(base_model=new_model,
                                                            field_str=new_field_str,
                                                            report_builder_class=new_report_builder_fields,
                                                            previous_base_model=base_model)
                    if result:
                        return result
        else:
            for include in report_builder_class.includes:
                app_label, model, report_builder_fields_str = include['model'].split('.')
                new_model = apps.get_model(app_label, model)
                new_report_builder_fields = getattr(new_model, report_builder_fields_str, None)
                if field_str == include['field']:
                    return new_report_builder_fields
        return None

    def _get_pivot_details(self, base_model, pivot_str, report_builder_class, previous_base_model=None):

        if '__' in pivot_str:
            pivot_parts = pivot_str.split('__')
            include_str = pivot_parts[0]
            new_pivot_str = '__'.join(pivot_parts[1:])

            for include in report_builder_class.includes:
                app_label, model, report_builder_fields_str = include['model'].split('.')
                new_model = apps.get_model(app_label, model)
                new_report_builder_fields = getattr(new_model, report_builder_fields_str, None)

                if new_model != previous_base_model and include_str == include['field']:
                    result = self._get_pivot_details(base_model=new_model,
                                                     pivot_str=new_pivot_str,
                                                     report_builder_class=new_report_builder_fields,
                                                     previous_base_model=base_model)
                    if result:
                        return result
        else:
            for pivot_field in report_builder_class.pivot_fields:
                if pivot_field['field'] == pivot_str:
                    return pivot_field
        return None
