from datetime import datetime, date, timedelta
from calendar import monthrange

from date_offset.date_offset import DateOffset


class VariableDate:
    RANGE_TYPE_TODAY = 1
    RANGE_TYPE_YESTERDAY = 2
    RANGE_TYPE_TOMORROW = 3
    RANGE_TYPE_THIS_WEEK = 4
    RANGE_TYPE_NEXT_WEEK = 5
    RANGE_TYPE_2_WEEKS_TIME = 6
    RANGE_TYPE_3_WEEKS_TIME = 34
    RANGE_TYPE_4_WEEKS_TIME = 35
    RANGE_TYPE_5_WEEKS_TIME = 36
    RANGE_TYPE_6_WEEKS_TIME = 37
    RANGE_TYPE_THIS_MONTH = 7
    RANGE_TYPE_NEXT_MONTH = 8
    RANGE_TYPE_LAST_MONTH = 9
    RANGE_TYPE_NEXT_7_DAYS = 10
    RANGE_TYPE_LAST_7_DAYS = 11
    RANGE_TYPE_NEXT_14_DAYS = 12
    RANGE_TYPE_LAST_14_DAYS = 13
    RANGE_TYPE_NEXT_28_DAYS = 14
    RANGE_TYPE_LAST_28_DAYS = 15
    RANGE_TYPE_THIS_YEAR = 16
    RANGE_TYPE_LAST_YEAR = 17
    RANGE_TYPE_LAST_WEEK = 18
    RANGE_TYPE_LAST_18_MONTHS = 23
    RANGE_TYPE_NEXT_2_MONTH = 24
    RANGE_TYPE_LAST_2_MONTH = 25
    RANGE_TYPE_NEXT_3_MONTH = 26
    RANGE_TYPE_LAST_3_MONTH = 27
    RANGE_TYPE_NEXT_6_MONTH = 28
    RANGE_TYPE_LAST_6_MONTH = 29
    RANGE_TYPE_NEXT_60_DAYS = 30
    RANGE_TYPE_LAST_60_DAYS = 31
    RANGE_TYPE_NEXT_90_DAYS = 32
    RANGE_TYPE_LAST_90_DAYS = 33

    RANGE_TYPE_CHOICES = ((RANGE_TYPE_LAST_6_MONTH, 'Last 6 months'),
                          (RANGE_TYPE_LAST_3_MONTH, 'Last 3 months'),
                          (RANGE_TYPE_LAST_90_DAYS, 'Last 90 days'),
                          (RANGE_TYPE_LAST_2_MONTH, 'Last 2 month'),
                          (RANGE_TYPE_LAST_60_DAYS, 'Last 60 days'),
                          (RANGE_TYPE_LAST_MONTH, 'Last month'),
                          (RANGE_TYPE_LAST_28_DAYS, 'Last 28 days'),
                          (RANGE_TYPE_LAST_14_DAYS, 'Last 14 days'),
                          (RANGE_TYPE_LAST_7_DAYS, 'Last 7 days'),
                          (RANGE_TYPE_LAST_WEEK, 'Last week'),
                          (RANGE_TYPE_YESTERDAY, 'Yesterday'),
                          (RANGE_TYPE_TODAY, 'Today'),
                          (RANGE_TYPE_TOMORROW, 'Tomorrow'),
                          (RANGE_TYPE_THIS_WEEK, 'This week'),
                          (RANGE_TYPE_NEXT_7_DAYS, 'Next 7 days'),
                          (RANGE_TYPE_NEXT_14_DAYS, 'Next 14 days'),
                          (RANGE_TYPE_NEXT_WEEK, 'Next week'),
                          (RANGE_TYPE_2_WEEKS_TIME, '2 weeks time'),
                          (RANGE_TYPE_3_WEEKS_TIME, '3 weeks time'),
                          (RANGE_TYPE_4_WEEKS_TIME, '4 weeks time'),
                          (RANGE_TYPE_5_WEEKS_TIME, '5 weeks time'),
                          (RANGE_TYPE_6_WEEKS_TIME, '6 weeks time'),
                          (RANGE_TYPE_THIS_MONTH, 'This month'),
                          (RANGE_TYPE_NEXT_28_DAYS, 'Next 28 days'),
                          (RANGE_TYPE_NEXT_MONTH, 'Next month'),
                          (RANGE_TYPE_NEXT_2_MONTH, 'Next 2 months'),
                          (RANGE_TYPE_NEXT_60_DAYS, 'Next 60 days'),
                          (RANGE_TYPE_NEXT_3_MONTH, 'Next 3 months'),
                          (RANGE_TYPE_NEXT_90_DAYS, 'Next 90 days'),
                          (RANGE_TYPE_NEXT_6_MONTH, 'Next 6 months'),
                          (RANGE_TYPE_THIS_YEAR, 'This year'),
                          (RANGE_TYPE_LAST_YEAR, 'Last year'),
                          (RANGE_TYPE_LAST_18_MONTHS, 'Last 18 months')
                          )

    def get_variable_dates(self, range_type):
        today = date.today()
        if range_type == self.RANGE_TYPE_TODAY:
            start_date = today
            end_date = today + timedelta(days=1)
            number_of_days = 1
        elif range_type == self.RANGE_TYPE_YESTERDAY:  # Yesterday
            start_date = today - timedelta(days=1)
            end_date = today
            number_of_days = 1
        elif range_type == self.RANGE_TYPE_TOMORROW:  # Tomorrow
            start_date = today + timedelta(days=1)
            end_date = start_date + timedelta(days=1)
            number_of_days = 1
        elif range_type == self.RANGE_TYPE_THIS_WEEK:  # This Week
            start_date = today - timedelta(days=today.weekday())
            end_date = start_date + timedelta(days=7)
            number_of_days = 7
        elif range_type == self.RANGE_TYPE_NEXT_WEEK:  # Next Week
            start_date = today - timedelta(days=today.weekday()) + timedelta(days=7)
            end_date = start_date + timedelta(days=7)
            number_of_days = 7
        elif range_type == self.RANGE_TYPE_LAST_WEEK:  # Last Week
            start_date = today - timedelta(days=today.weekday()) + timedelta(days=14)
            end_date = start_date + timedelta(days=7)
            number_of_days = 7
        elif range_type == self.RANGE_TYPE_2_WEEKS_TIME:  # 2 Week Time
            start_date = today - timedelta(days=today.weekday()) + timedelta(days=14)
            end_date = start_date + timedelta(days=7)
            number_of_days = 7
        elif range_type == self.RANGE_TYPE_3_WEEKS_TIME:  # 3 Week Time
            start_date = today - timedelta(days=today.weekday()) + timedelta(days=21)
            end_date = start_date + timedelta(days=7)
            number_of_days = 7
        elif range_type == self.RANGE_TYPE_4_WEEKS_TIME:  # 4 Week Time
            start_date = today - timedelta(days=today.weekday()) + timedelta(days=28)
            end_date = start_date + timedelta(days=7)
            number_of_days = 7
        elif range_type == self.RANGE_TYPE_5_WEEKS_TIME:  # 5 Week Time
            start_date = today - timedelta(days=today.weekday()) + timedelta(days=35)
            end_date = start_date + timedelta(days=7)
            number_of_days = 7
        elif range_type == self.RANGE_TYPE_6_WEEKS_TIME:  # 6 Week Time
            start_date = today - timedelta(days=today.weekday()) + timedelta(days=42)
            end_date = start_date + timedelta(days=7)
            number_of_days = 7
        elif range_type == self.RANGE_TYPE_THIS_MONTH:  # This Month
            start_date = date(today.year, today.month, 1)
            number_of_days = monthrange(today.year, today.month)[1]
            end_date = start_date + timedelta(days=number_of_days - 1)
        elif range_type == self.RANGE_TYPE_NEXT_MONTH:  # Next Month
            number_of_days_in_this_month = monthrange(today.year, today.month)[1]
            start_date = (date(today.year, today.month, 1) +
                          timedelta(days=number_of_days_in_this_month))
            number_of_days = monthrange(start_date.year, start_date.month)[1]
            end_date = start_date + timedelta(days=number_of_days)
        elif range_type == self.RANGE_TYPE_LAST_MONTH:  # Last Month
            end_date = date(today.year, today.month, 1) - timedelta(days=1)
            last_month = end_date
            start_date = date(last_month.year, last_month.month, 1)
            number_of_days = (end_date - start_date).days
        elif range_type == self.RANGE_TYPE_NEXT_7_DAYS:  # Next 7 Days
            start_date = today
            end_date = start_date + timedelta(days=7)
            number_of_days = 7
        elif range_type == self.RANGE_TYPE_LAST_7_DAYS:  # Last 7 Days
            start_date = today - timedelta(days=6)
            end_date = today
            number_of_days = 7
        elif range_type == self.RANGE_TYPE_NEXT_14_DAYS:  # Next 14 Days
            start_date = today
            end_date = start_date + timedelta(days=14)
            number_of_days = 14
        elif range_type == self.RANGE_TYPE_LAST_14_DAYS:  # Next 14 Days
            start_date = today - timedelta(days=14)
            end_date = today
            number_of_days = 14
        elif range_type == 13:  # Last 14 Days
            start_date = today - timedelta(days=14)
            end_date = today
            number_of_days = 14
        elif range_type == self.RANGE_TYPE_NEXT_28_DAYS:  # Next 28 Days
            start_date = today
            end_date = start_date + timedelta(days=28)
            number_of_days = 28
        elif range_type == self.RANGE_TYPE_LAST_28_DAYS:  # Last 28 Days
            start_date = today - timedelta(days=28)
            end_date = today
            number_of_days = 28
        elif range_type == self.RANGE_TYPE_NEXT_60_DAYS:  # Next 60 Days
            start_date = today
            end_date = start_date + timedelta(days=60)
            number_of_days = 60
        elif range_type == self.RANGE_TYPE_LAST_60_DAYS:  # Last 60 Days
            start_date = today - timedelta(days=60)
            end_date = today
            number_of_days = 60
        elif range_type == self.RANGE_TYPE_NEXT_90_DAYS:  # Next 90 Days
            start_date = today
            end_date = start_date + timedelta(days=90)
            number_of_days = 90
        elif range_type == self.RANGE_TYPE_LAST_90_DAYS:  # Last 90 Days
            start_date = today - timedelta(days=90)
            end_date = today
            number_of_days = 90
        elif range_type == self.RANGE_TYPE_THIS_YEAR:  # This Year
            start_date = date(today.year, 1, 1)
            end_date = date(today.year, 12, 31)
            number_of_days = (end_date - start_date).days
        elif range_type == self.RANGE_TYPE_LAST_YEAR:  # Last Year
            last_year = today.year - 1
            start_date = date(last_year, 1, 1)
            end_date = date(last_year, 12, 31)
            number_of_days = (end_date - start_date).days
        elif range_type == self.RANGE_TYPE_LAST_18_MONTHS:
            date_offset = DateOffset()
            start_date = date_offset.get_offset('-18m', today)
            end_date = today
            number_of_days = (end_date - start_date).days
        elif range_type == self.RANGE_TYPE_LAST_2_MONTH:
            date_offset = DateOffset()
            start_date = date_offset.get_offset('-2m', today)
            end_date = today
            number_of_days = (end_date - start_date).days
        elif range_type == self.RANGE_TYPE_NEXT_2_MONTH:
            date_offset = DateOffset()
            start_date = today
            end_date = date_offset.get_offset('2m', today)
            number_of_days = (end_date - start_date).days
        elif range_type == self.RANGE_TYPE_LAST_3_MONTH:
            date_offset = DateOffset()
            start_date = date_offset.get_offset('-3m', today)
            end_date = today
            number_of_days = (end_date - start_date).days
        elif range_type == self.RANGE_TYPE_NEXT_3_MONTH:
            date_offset = DateOffset()
            start_date = today
            end_date = date_offset.get_offset('3m', today)
            number_of_days = (end_date - start_date).days
        elif range_type == self.RANGE_TYPE_LAST_6_MONTH:
            date_offset = DateOffset()
            start_date = date_offset.get_offset('-6m', today)
            end_date = today
            number_of_days = (end_date - start_date).days
        elif range_type == self.RANGE_TYPE_NEXT_6_MONTH:
            date_offset = DateOffset()
            start_date = today
            end_date = date_offset.get_offset('6m', today)
            number_of_days = (end_date - start_date).days
        else:
            assert False, 'unknown date value'

        start_date_and_time = datetime.combine(start_date, datetime.min.time())
        end_date_and_time = datetime.combine(end_date, datetime.max.time())

        return start_date_and_time, end_date_and_time, number_of_days

    def get_variable_date_filter_values(self):
        values = {}
        for choice in self.RANGE_TYPE_CHOICES:
            values['#variable_date:%d' % choice[0]] = choice[1]
        return values
