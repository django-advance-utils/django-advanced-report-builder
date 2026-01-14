import calendar
import datetime
import operator
from functools import reduce

from django.apps import apps
from django.conf import settings
from django.db.models import F, Q
from django.db.models.functions import ExtractWeekDay
from django.shortcuts import get_object_or_404

from advanced_report_builder.exceptions import ReportError
from advanced_report_builder.field_utils import ReportBuilderFieldUtils
from advanced_report_builder.models import ReportOption, ReportQuery
from advanced_report_builder.utils import get_report_builder_class, try_int
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

    def get_day_period(self):
        if not self.min_date or not self.max_date:
            return None

        min_d = self.min_date.date()
        max_d = self.max_date.date()

        if min_d == max_d:
            return min_d, max_d
        return None

    def get_week_period(self):
        if not self.min_date or not self.max_date:
            return None

        min_d = self.min_date.date()
        max_d = self.max_date.date()

        if (max_d - min_d).days != 6:
            return None

        return min_d, max_d

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

    def get_quarter_period(self):
        if not self.min_date or not self.max_date:
            return None

        min_d = self.min_date.date()
        max_d = self.max_date.date()

        # Must start on first of a month
        if min_d.day != 1:
            return None

        # Must end on last day of a month
        last_day = calendar.monthrange(max_d.year, max_d.month)[1]
        if max_d.day != last_day:
            return None

        # Calculate number of months spanned (inclusive)
        months = (max_d.year - min_d.year) * 12 + (max_d.month - min_d.month) + 1

        if months != 3:
            return None

        return min_d, max_d

    def get_year_period(self):
        if not self.min_date or not self.max_date:
            return None

        min_d = self.min_date.date()
        max_d = self.max_date.date()

        # Must start on first day of a month
        if min_d.day != 1:
            return None

        # Must end on last day of a month
        last_day = calendar.monthrange(max_d.year, max_d.month)[1]
        if max_d.day != last_day:
            return None

        # Must span exactly 12 months
        months = (max_d.year - min_d.year) * 12 + (max_d.month - min_d.month) + 1
        if months != 12:
            return None

        return min_d, max_d


class FilterQueryMixin:
    def __init__(self, *args, **kwargs):
        self.report = None
        self.dashboard_report = None
        self.enable_edit = None
        self.slug = None
        self.base_model = None
        self.period_data = PeriodData()
        self._held_report_query = None
        self._report_options_data = None
        super().__init__(*args, **kwargs)

    def process_query_filters(self, query, search_filter_data, extra_filter_data=None, extra_filter=None):
        annotations = {}
        result = self.process_filters(
            search_filter_data=search_filter_data,
            annotations=annotations,
            extra_filter_data=extra_filter_data,
            extra_filter=extra_filter,
        )
        if annotations:
            query = query.annotate(**annotations)
        if result:
            return query.filter(result)
        return query

    def process_filters(
        self, search_filter_data, extra_filter_data=None, annotations=None, extra_filter=None, prefix_field_name=None
    ):
        if not search_filter_data and not extra_filter_data:
            return []

        query_list = []
        extra_query_list = []
        reduce_by = operator.and_
        if search_filter_data:
            query_list = self._process_group(
                query_data=search_filter_data, prefix_field_name=prefix_field_name, annotations=annotations
            )
            reduce_by = self._format_group_conditions(display_condition=search_filter_data['condition'])
        if extra_filter_data:
            extra_query_list = self._process_group(
                query_data=extra_filter_data, prefix_field_name=prefix_field_name, annotations=annotations
            )

        if len(query_list) == 0:
            query_list = extra_query_list
        elif len(query_list) > 0 and len(extra_query_list) > 0:
            query_list[0] = extra_query_list[0] & query_list[0]

        if extra_filter:
            query_list.append(extra_filter)

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
            elif data_type == 'string' and _id.endswith('__financial_variable_year'):
                self.get_variable_financial_year(
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
            elif data_type == 'string' and _id.endswith('__week_number'):
                self.get_week_number(
                    value=value,
                    query_list=query_list,
                    display_operator=display_operator,
                    field=field,
                    query_string=query_string,
                )
            elif data_type == 'string' and _id.endswith('__financial_week_number'):
                fy_start = self.get_financial_year(rules=query_data['rules'])
                self.get_financial_week_number(
                    value=value,
                    query_list=query_list,
                    display_operator=display_operator,
                    field=field,
                    query_string=query_string,
                    fy_start=fy_start,
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

    def get_financial_year(self, rules):
        for rule in rules:
            if 'condition' in rule:
                continue

            if rule['operator'] != 'equal':
                continue

            data_type = rule['type']
            value = rule.get('value')
            _id = rule['id']

            # 1) Variable Date → Financial Year
            if data_type == 'string' and _id.endswith('__variable_date'):
                _, range_type = str(value).split(':')
                range_type = int(range_type)

                if range_type in (
                    VariableDate.RANGE_TYPE_LAST_FINANCIAL_YEAR,
                    VariableDate.RANGE_TYPE_THIS_FINANCIAL_YEAR,
                    VariableDate.RANGE_TYPE_NEXT_FINANCIAL_YEAR,
                ):
                    variable_date = VariableDate()
                    dates = variable_date.get_variable_dates(
                        range_type=range_type,
                        financial_year_start_month=self.get_financial_month(),
                    )
                    return dates[0]

            # 2) Explicit Financial Year (value IS the year)
            elif data_type == 'string' and _id.endswith('__financial_variable_year'):
                _, year = str(value).split(':')
                year = int(year)
                start_month = self.get_financial_month()
                return datetime.date(year, start_month, 1)

        return None

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
            value = variable_date.get_variable_dates(
                range_type=int(range_type), financial_year_start_month=self.get_financial_month()
            )

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

    def get_variable_financial_year(
        self,
        value,
        query_list,
        display_operator,
        field,
        query_string,
    ):
        if display_operator in ['is_null', 'is_not_null']:
            query_list.append(Q((query_string, value)))
            return

        _, year = value.split(':')
        year = int(year)

        start_month = self.get_financial_month()

        start_date = datetime.date(year, start_month, 1)
        end_date = datetime.date(year + 1, start_month, 1) - datetime.timedelta(days=1)

        if display_operator in [
            'less',
            'less_or_equal',
            'greater',
            'greater_or_equal',
        ]:
            if display_operator == 'less':
                query_list.append(Q(**{f'{field}__lt': start_date}))
                self.set_min_max_date(date_in=start_date)

            elif display_operator == 'less_or_equal':
                query_list.append(Q(**{f'{field}__lte': end_date}))
                self.set_min_max_date(date_in=end_date)

            elif display_operator == 'greater':
                query_list.append(Q(**{f'{field}__gt': end_date}))
                self.set_min_max_date(date_in=end_date)

            elif display_operator == 'greater_or_equal':
                query_list.append(Q(**{f'{field}__gte': start_date}))
                self.set_min_max_date(date_in=start_date)

        elif display_operator in ['not_equal', 'not_in']:
            query_list.append(~(Q(**{f'{field}__gte': start_date}) & Q(**{f'{field}__lte': end_date})))

        else:  # equal / in
            query_list.append(Q(**{f'{field}__gte': start_date}) & Q(**{f'{field}__lte': end_date}))
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

    @staticmethod
    def get_week_number(value, query_list, display_operator, field, query_string):
        if display_operator in ['is_null', 'is_not_null']:
            query_list.append(Q((query_string, value)))
            return

        week = int(value)

        operator_map = {
            'equal': '',
            'not_equal': '',
            'less': '__lt',
            'less_or_equal': '__lte',
            'greater': '__gt',
            'greater_or_equal': '__gte',
        }

        lookup = operator_map.get(display_operator)
        if lookup is None:
            return

        key = f'{field}__week{lookup}'
        q = Q(**{key: week})

        if display_operator == 'not_equal':
            query_list.append(~q)
        else:
            query_list.append(q)

    @staticmethod
    def get_financial_week_number(
        value,
        query_list,
        display_operator,
        field,
        query_string,
        *,
        fy_start,
    ):
        """
        Applies a Financial Week Number filter.

        Financial weeks are calculated relative to the financial year start date.
        Week 1 begins at fy_start and each week spans 7 days.
        """

        if display_operator in ['is_null', 'is_not_null']:
            query_list.append(Q((query_string, value)))
            return

        if fy_start is None:
            raise ReportError(
                'Financial Week Number requires a Financial Year '
                '(select a Financial Year or use a Financial Year date range).'
            )

        week = int(value)

        if not 1 <= week <= 53:
            raise ReportError('Financial Week Number must be between 1 and 53')

        week_start = fy_start + datetime.timedelta(days=(week - 1) * 7)
        week_end = week_start + datetime.timedelta(days=7)

        if display_operator == 'equal':
            query_list.append(Q(**{f'{field}__gte': week_start}) & Q(**{f'{field}__lt': week_end}))

        elif display_operator == 'not_equal':
            query_list.append(~(Q(**{f'{field}__gte': week_start}) & Q(**{f'{field}__lt': week_end})))

        elif display_operator == 'less':
            query_list.append(Q(**{f'{field}__lt': week_start}))

        elif display_operator == 'less_or_equal':
            query_list.append(Q(**{f'{field}__lt': week_end}))

        elif display_operator == 'greater':
            query_list.append(Q(**{f'{field}__gte': week_end}))

        elif display_operator == 'greater_or_equal':
            query_list.append(Q(**{f'{field}__gte': week_start}))

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
            extra_title_parts = []
            report_queries_count = self.report.reportquery_set.all().count()
            if report_queries_count > 1:
                version_name = self.get_report_query(report=self.report).name
                extra_title_parts.append(version_name)
            report_options_data = self.get_report_options_data()
            report_options = report_options_data['report_options']
            report_options_dict = report_options_data['report_options_dict']

            for report_option in report_options:
                base_model = report_option.content_type.model_class()
                report_cls = get_report_builder_class(
                    model=base_model, class_name=report_option.report_builder_class_name
                )

                _obj = base_model.objects.filter(pk=report_options_dict.get(report_option.pk)).first()
                if _obj is not None:
                    method = getattr(_obj, report_cls.option_label, None)
                    label = method() if callable(method) else _obj.__str__()
                    extra_title_parts.append(label)

            if extra_title_parts:
                extra_title_parts = ' - '.join(extra_title_parts)
                title = f'{title} ({extra_title_parts})'

            return title

    def get_report_option_query(self):
        report_options_data = self.get_report_options_data()
        report_options = report_options_data['report_options']
        report_options_dict = report_options_data['report_options_dict']
        # build query
        query = Q()

        for report_option in report_options:
            value = report_options_dict.get(report_option.id)
            if value:
                query &= Q(**{f'{report_option.field}_id': value})

        return query

    def get_report_options_data(self):
        if self._report_options_data is None:
            report_options_dict = {}
            dashboard_report = self.dashboard_report
            dashboard_report_id = dashboard_report.id if dashboard_report else None

            # dashboard-level overrides (primary)
            if dashboard_report and dashboard_report.options:
                for k, v in dashboard_report.options.items():
                    if not k.startswith('option'):
                        continue
                    try:
                        key = int(k[len('option') :])
                    except ValueError:
                        continue
                    report_options_dict[key] = try_int(v)

            if self.slug is not None:
                # options from slug
                for k, v in self.slug.items():
                    if not k.startswith('option'):
                        continue
                    key = k[len('option') :]
                    if isinstance(key, str) and '_' in key:
                        key, option_database_board_id = key.split('_', 1)
                        if dashboard_report_id != try_int(option_database_board_id):
                            continue
                    key = try_int(key)
                    report_options_dict[key] = try_int(v)

            report_options = ReportOption.objects.filter(report=self.report, id__in=report_options_dict.keys())
            self._report_options_data = {'report_options': report_options, 'report_options_dict': report_options_dict}

        return self._report_options_data

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
