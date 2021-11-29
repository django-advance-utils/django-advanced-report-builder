import json
import operator
from functools import reduce

from django.db.models import Q

from advanced_report_builder.variable_date import VariableDate


class FilterQueryMixin:

    def process_filters(self, query, search_filter_data):
        if not search_filter_data:
            return query

        query_data = json.loads(search_filter_data)
        query_list = self._process_group(query_data=query_data)
        reduce_by = self._format_group_conditions(query_data['condition'])

        if query_list:
            return query.filter(reduce(reduce_by, query_list))

        return query

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
