import calendar
import datetime
import operator
from functools import reduce

from django.apps import apps
from django.db.models import F, Q
from django.db.models.functions import ExtractWeekDay
from django.shortcuts import get_object_or_404
from django.conf import settings

from advanced_report_builder.field_utils import ReportBuilderFieldUtils
from advanced_report_builder.models import ReportQuery
from advanced_report_builder.utils import get_report_builder_class
from advanced_report_builder.variable_date import VariableDate


class PeriodData:
    min_date = None
    max_date = None

    def set_min_max_date(self, date_in):
        dt = (
            datetime.datetime.combine(date_in, datetime.datetime.min.time())
            if isinstance(date_in, datetime.date) and not isinstance(date_in, datetime.datetime)
            else date_in
        )

        if self.min_date is None or dt < self.min_date:
            self.min_date = dt

        if self.max_date is None or dt > self.max_date:
            self.max_date = dt

    import calendar

    def get_month_period(self):
        if not self.min_date or not self.max_date:
            return None

        # Normalize to date (drop time)
        min_d = self.min_date.date()
        max_d = self.max_date.date()

        # Check if in the same year and month
        if min_d.year != max_d.year or min_d.month != max_d.month:
            return None

        # First day of the month
        start_of_month = min_d.replace(day=1)

        # Last day of the month
        last_day = calendar.monthrange(max_d.year, max_d.month)[1]
        end_of_month = max_d.replace(day=last_day)

        if min_d == start_of_month and max_d == end_of_month:
            return min_d, max_d
        return None


class FilterQueryMixin:
    def __init__(self, *args, **kwargs):
        self.report = None
        self.dashboard_report = None
        self.enable_edit = None
        self.slug = None
        self.base_model = None
        self.period_data = PeriodData()
        self._held_report_query = None
        super().__init__(*args, **kwargs)

    def process_query_filters(self, query, search_filter_data):
        annotations = {}
        result = self.process_filters(search_filter_data=search_filter_data, annotations=annotations)
        if annotations:
            query = query.annotate(**annotations)
        if result:
            return query.filter(result)
        return query

    def process_filters(self, search_filter_data, annotations=None, extra_filter=None, prefix_field_name=None):
        if not search_filter_data:
            return []

        query_list = self._process_group(
            query_data=search_filter_data, prefix_field_name=prefix_field_name, annotations=annotations
        )
        if extra_filter:
            query_list.append(extra_filter)

        reduce_by = self._format_group_conditions(display_condition=search_filter_data['condition'])

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
        reduce_by = operator.and_ if display_condition == 'AND' else operator.or_

        return reduce_by

    def _process_group(self, query_data, prefix_field_name, annotations):
        query_list = []

        for rule in query_data['rules']:
            if condition := rule.get('condition'):
                reduce_by = self._format_group_conditions(display_condition=condition)
                sub_query_list = self._process_group(
                    query_data=rule, prefix_field_name=prefix_field_name, annotations=annotations
                )
                if sub_query_list:
                    query_list.append(reduce(reduce_by, sub_query_list))
                continue

            field = rule['field']
            if prefix_field_name is not None:
                field = prefix_field_name + '__' + field
            _id = rule['id']
            display_operator = rule['operator']
            query_string = field + self._get_operator(display_operator)
            data_type = rule['type']
            value = rule.get('value', '')
            if display_operator == 'is_null':
                value = True
            elif display_operator == 'is_not_null':
                value = False

            if _id.endswith('__field_vs_field'):
                self.field_vs_field(
                    value=value, query_list=query_list, display_operator=display_operator, query_string=query_string
                )
            elif data_type == 'string' and _id.endswith('__variable_date'):
                self.get_variable_date(
                    value=value,
                    query_list=query_list,
                    display_operator=display_operator,
                    field=field,
                    query_string=query_string,
                )
            elif data_type == 'string' and _id.endswith('__variable_year'):
                self.get_variable_year(
                    value=value,
                    query_list=query_list,
                    display_operator=display_operator,
                    field=field,
                    query_string=query_string,
                )
            elif data_type == 'string' and _id.endswith('__variable_month'):
                self.get_variable_month(
                    value=value,
                    query_list=query_list,
                    display_operator=display_operator,
                    field=field,
                    query_string=query_string,
                )
            elif data_type == 'string' and _id.endswith('__variable_quarter'):
                self.get_variable_quarter(
                    value=value,
                    query_list=query_list,
                    display_operator=display_operator,
                    field=field,
                    query_string=query_string,
                )
            elif data_type == 'string' and _id.endswith('__variable_day'):
                self.get_variable_day(
                    value=value,
                    query_list=query_list,
                    display_operator=display_operator,
                    field=field,
                    annotations=annotations,
                )
            elif data_type == 'string' and _id.endswith('__logged_in_user'):
                self.get_logged_in_user(
                    value=value,
                    query_list=query_list,
                    display_operator=display_operator,
                    query_string=query_string,
                )
            else:
                # 'Normal' Query.
                if display_operator in [
                    'not_equal',
                    'not_in',
                    'not_contains',
                    'not_begins_with',
                    'not_ends_with',
                ]:
                    query_list.append(~Q((query_string, value)))
                else:
                    query_list.append(Q((query_string, value)))

        return query_list

    @staticmethod
    def field_vs_field(value, query_list, display_operator, query_string):
        if display_operator == 'not_equal':
            query_list.append(~Q(**{query_string: F(value)}))
        else:
            query_list.append(Q(**{query_string: F(value)}))

    def set_min_max_date(self, date_in):
        self.period_data.set_min_max_date(date_in)

    def get_variable_date(self, value, query_list, display_operator, field, query_string):
        if display_operator in ['is_null', 'is_not_null']:
            query_list.append(Q((query_string, value)))
        else:
            _, range_type = value.split(':')
            variable_date = VariableDate()
            value = variable_date.get_variable_dates(range_type=int(range_type),
                                                     financial_year_start_month=self.get_financial_month())

            if display_operator in ['less', 'greater_or_equal']:
                query_list.append(Q((query_string, value[0])))
                if display_operator == 'less':
                    self.set_min_max_date(date_in=value[0])
                else:
                    self.set_min_max_date(date_in=value[0])
                    self.set_min_max_date(date_in=value[1])

            elif display_operator in ['greater', 'less_or_equal']:
                query_list.append(Q((query_string, value[1])))
                if display_operator == 'greater':
                    self.set_min_max_date(date_in=value[1])
                else:
                    self.set_min_max_date(date_in=value[0])
                    self.set_min_max_date(date_in=value[1])
            elif display_operator in ['not_equal', 'not_in']:
                query_list.append(~((Q((field + '__gte', value[0]))) & (Q((field + '__lte', value[1])))))
            else:
                query_list.append((Q((field + '__gte', value[0]))) & (Q((field + '__lte', value[1]))))
                self.set_min_max_date(date_in=value[0])
                self.set_min_max_date(date_in=value[1])

    def get_variable_year(self, value, query_list, display_operator, field, query_string):
        if display_operator in ['is_null', 'is_not_null']:
            query_list.append(Q((query_string, value)))
        else:
            _, year = value.split(':')
            year = int(year)
            start_date = datetime.date(year, 1, 1)
            end_date = datetime.date(year, 12, 31)

            if display_operator in [
                'less',
                'less_or_equal',
                'greater',
                'greater_or_equal',
            ]:
                query_string_parts = query_string.split('__')
                query_list.append(Q((f'{field}__year__{query_string_parts[-1]}', year)))

                if display_operator == 'greater':
                    self.set_min_max_date(date_in=end_date)
                elif display_operator == 'less':
                    self.set_min_max_date(date_in=start_date)
                else:
                    self.set_min_max_date(date_in=start_date)
                    self.set_min_max_date(date_in=end_date)

            elif display_operator in ['not_equal', 'not_in']:
                query_list.append(~Q((query_string + '__year', year)))
            else:
                query_list.append(Q((query_string + '__year', year)))
                self.set_min_max_date(date_in=start_date)
                self.set_min_max_date(date_in=end_date)

    @staticmethod
    def get_variable_month(value, query_list, display_operator, field, query_string):
        if display_operator in ['is_null', 'is_not_null']:
            query_list.append(Q((query_string, value)))
        else:
            _, month = value.split(':')
            month = int(month)
            if display_operator in ['not_equal', 'not_in']:
                query_list.append(~Q((field + '__month', month)))
            else:
                query_list.append(Q((field + '__month', month)))

    def get_variable_quarter(self, value, query_list, display_operator, field, query_string):
        if display_operator in ['is_null', 'is_not_null']:
            query_list.append(Q((query_string, value)))
        else:
            quarter_type, quarter = value.split(':')
            quarter = int(quarter)
            if quarter_type == '#quarter':
                start_month = (quarter - 1) * 3
                end_month = start_month + 3
                if display_operator == 'not_equal':
                    query_list.append(
                        ~((Q((field + '__month__gt', start_month))) & (Q((field + '__month__lte', end_month))))
                    )
                else:
                    query_list.append(
                        (Q((field + '__month__gt', start_month))) & (Q((field + '__month__lte', end_month)))
                    )
            else:
                start_month = self.get_financial_month() - 1
                end_month = start_month + 3
                months = [divmod(x, 12)[1] + 1 for x in range(start_month, end_month)]

                if display_operator == 'not_equal':
                    query_list.append(
                        ~(
                            (Q((field + '__month', months[0])))
                            | (Q((field + '__month', months[1])))
                            | (Q((field + '__month', months[2])))
                        )
                    )
                else:
                    query_list.append(
                        (Q((field + '__month', months[0])))
                        | (Q((field + '__month', months[1])))
                        | (Q((field + '__month', months[2])))
                    )

    @staticmethod
    def get_variable_day(value, query_list, display_operator, field, annotations):
        if annotations is None:
            # maybe create a warning.  As this won't work with sub queries
            return

        annotate_name = f'{field}_weekday'
        annotations[annotate_name] = ExtractWeekDay(field)
        if display_operator == 'not_equal':
            query_list.append(~Q(**{f'{annotate_name}': value}))
        else:
            query_list.append(Q(**{f'{annotate_name}': value}))

    def get_logged_in_user(self, value, query_list, display_operator, query_string):
        # noinspection PyUnresolvedReferences
        current_user = self.request.user
        value = value == '1'
        if (display_operator == 'equal' and value) or (display_operator == 'not_equal' and not value):
            query_list.append(Q((query_string, current_user)))
        else:
            query_list.append(~Q((query_string, current_user)))

    def get_report_query(self, report):
        if self._held_report_query is not None:
            return self._held_report_query

        dashboard_report = self.dashboard_report
        if dashboard_report is not None:
            slug_key = self.slug.get(f'query{report.pk}_{dashboard_report.pk}')
        else:
            slug_key = self.slug.get(f'query{report.pk}')
        if slug_key:
            report_query = get_object_or_404(ReportQuery, id=slug_key)
            if report_query.report_id != report.pk:
                return None
        else:
            if dashboard_report is not None and dashboard_report.report_query is not None:
                report_query = dashboard_report.report_query
            else:
                report_query = report.reportquery_set.first()
        self._held_report_query = report_query
        return self._held_report_query

    @staticmethod
    def apply_order_by(query, report_query, base_model, report_type):
        order_by = []
        utils = ReportBuilderFieldUtils()
        report_builder_class = get_report_builder_class(model=base_model, report_type=report_type)
        for report_query_order in report_query.reportqueryorder_set.all():
            field_name = report_query_order.order_by_field
            field_name = utils.get_field_details(
                base_model=base_model,
                field=field_name,
                report_builder_class=report_builder_class,
            )[3]
            if report_query_order.order_by_ascending:
                order_by.append(field_name)
            else:
                order_by.append(f'-{field_name}')
        if len(order_by) > 0:
            query = query.order_by(*order_by)
        return query

    def get_title(self):
        if self.dashboard_report and self.dashboard_report.name_override:
            return self.dashboard_report.name_override
        else:
            title = self.report.name
            report_queries_count = self.report.reportquery_set.all().count()
            if report_queries_count > 1:
                version_name = self.get_report_query(report=self.report).name
                title += f' ({version_name})'
            return title


    def _get_report_builder_class(self, base_model, field_str, report_builder_class, previous_base_model=None):
        if '__' in field_str:
            field_parts = field_str.split('__')
            include_str = field_parts[0]
            new_field_str = '__'.join(field_parts[1:])

            include = report_builder_class.includes.get(include_str)

            if include is not None:
                app_label, model, report_builder_fields_str = include['model'].split('.')
                new_model = apps.get_model(app_label, model)

                new_report_builder_class = get_report_builder_class(
                    model=new_model, class_name=report_builder_fields_str
                )

                if new_model != previous_base_model:
                    result = self._get_report_builder_class(
                        base_model=new_model,
                        field_str=new_field_str,
                        report_builder_class=new_report_builder_class,
                        previous_base_model=base_model,
                    )
                    if result:
                        return result
        else:
            include = report_builder_class.includes.get(field_str)
            if include is not None:
                app_label, model, report_builder_fields_str = include['model'].split('.')
                new_model = apps.get_model(app_label, model)
                new_report_builder_class = get_report_builder_class(
                    model=new_model, class_name=report_builder_fields_str
                )

                return new_report_builder_class
        return None

    def _get_pivot_details(
        self,
        base_model,
        pivot_str,
        report_builder_class,
        previous_base_model=None,
        include_str='',
    ):
        if pivot_str in report_builder_class.pivot_fields:
            pivot_data = report_builder_class.pivot_fields[pivot_str]
            full_field_id = pivot_data['field'] if include_str == '' else '__'.join((include_str, pivot_data['field']))

            return {'id': full_field_id, 'details': pivot_data}

        if '__' in pivot_str:
            pivot_parts = pivot_str.split('__')
            include_str = pivot_parts[0]
            new_pivot_str = '__'.join(pivot_parts[1:])

            include = report_builder_class.includes.get(include_str)
            if include is not None:
                app_label, model, report_builder_fields_str = include['model'].split('.')
                new_model = apps.get_model(app_label, model)
                new_report_builder_class = get_report_builder_class(
                    model=new_model, class_name=report_builder_fields_str
                )
                if new_model != previous_base_model:
                    result = self._get_pivot_details(
                        base_model=new_model,
                        pivot_str=new_pivot_str,
                        report_builder_class=new_report_builder_class,
                        previous_base_model=base_model,
                        include_str=include_str,
                    )
                    if result:
                        return result
        return None

    def get_financial_month(self):
        month = getattr(settings, 'FINANCIAL_YEAR_START_MONTH', 1)
        return month if 1 <= month <= 12 else 1
