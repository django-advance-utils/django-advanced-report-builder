import calendar
from calendar import monthrange
from datetime import date, datetime, timedelta

from date_offset.date_offset import DateOffset
from dateutil.relativedelta import relativedelta


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
    RANGE_TYPE_LAST_12_MONTHS = 38
    RANGE_TYPE_NEXT_12_MONTHS = 39
    RANGE_TYPE_LAST_WEEK = 18

    RANGE_TYPE_NEXT_2_MONTHS = 24
    RANGE_TYPE_LAST_2_MONTHS = 25
    RANGE_TYPE_NEXT_3_MONTHS = 26
    RANGE_TYPE_LAST_3_MONTHS = 27
    RANGE_TYPE_NEXT_6_MONTHS = 28
    RANGE_TYPE_LAST_6_MONTHS = 29
    RANGE_TYPE_NEXT_60_DAYS = 30
    RANGE_TYPE_LAST_60_DAYS = 31
    RANGE_TYPE_NEXT_90_DAYS = 32
    RANGE_TYPE_LAST_90_DAYS = 33
    RANGE_TYPE_LAST_18_MONTHS = 23
    RANGE_TYPE_LAST_24_MONTHS = 40
    RANGE_TYPE_NEXT_24_MONTHS = 41
    RANGE_TYPE_LAST_36_MONTHS = 42
    RANGE_TYPE_NEXT_36_MONTHS = 43

    RANGE_TYPE_2_WEEKS_AGO = 44
    RANGE_TYPE_3_WEEKS_AGO = 45
    RANGE_TYPE_4_WEEKS_AGO = 46
    RANGE_TYPE_5_WEEKS_AGO = 47
    RANGE_TYPE_6_WEEKS_AGO = 48

    RANGE_TYPE_THIS_YEAR = 16
    RANGE_TYPE_LAST_YEAR = 17

    # Financial year ranges
    RANGE_TYPE_LAST_FINANCIAL_YEAR = 49
    RANGE_TYPE_THIS_FINANCIAL_YEAR = 50
    RANGE_TYPE_NEXT_FINANCIAL_YEAR = 51

    # Last FY quarters
    RANGE_TYPE_LAST_FINANCIAL_YEAR_Q1 = 52
    RANGE_TYPE_LAST_FINANCIAL_YEAR_Q2 = 53
    RANGE_TYPE_LAST_FINANCIAL_YEAR_Q3 = 54
    RANGE_TYPE_LAST_FINANCIAL_YEAR_Q4 = 55

    # This FY quarters
    RANGE_TYPE_THIS_FINANCIAL_YEAR_Q1 = 56
    RANGE_TYPE_THIS_FINANCIAL_YEAR_Q2 = 57
    RANGE_TYPE_THIS_FINANCIAL_YEAR_Q3 = 58
    RANGE_TYPE_THIS_FINANCIAL_YEAR_Q4 = 59

    # Next FY quarters
    RANGE_TYPE_NEXT_FINANCIAL_YEAR_Q1 = 60
    RANGE_TYPE_NEXT_FINANCIAL_YEAR_Q2 = 61
    RANGE_TYPE_NEXT_FINANCIAL_YEAR_Q3 = 62
    RANGE_TYPE_NEXT_FINANCIAL_YEAR_Q4 = 63

    # Current FY quarters
    RANGE_TYPE_LAST_FINANCIAL_QUARTER = 64
    RANGE_TYPE_CURRENT_FINANCIAL_QUARTER = 65
    RANGE_TYPE_NEXT_FINANCIAL_QUARTER = 66
    RANGE_TYPE_LAST_YEAR_SAME_FINANCIAL_QUARTER = 67

    # This calendar quarter
    RANGE_TYPE_LAST_CALENDAR_QUARTER = 68
    RANGE_TYPE_THIS_CALENDAR_QUARTER = 69
    RANGE_TYPE_NEXT_CALENDAR_QUARTER = 70

    # Last calendar quarters
    RANGE_TYPE_LAST_CALENDAR_YEAR_Q1 = 71
    RANGE_TYPE_LAST_CALENDAR_YEAR_Q2 = 72
    RANGE_TYPE_LAST_CALENDAR_YEAR_Q3 = 73
    RANGE_TYPE_LAST_CALENDAR_YEAR_Q4 = 74

    # This calendar quarters
    RANGE_TYPE_THIS_CALENDAR_YEAR_Q1 = 75
    RANGE_TYPE_THIS_CALENDAR_YEAR_Q2 = 76
    RANGE_TYPE_THIS_CALENDAR_YEAR_Q3 = 77
    RANGE_TYPE_THIS_CALENDAR_YEAR_Q4 = 78

    # Next calendar quarters
    RANGE_TYPE_NEXT_CALENDAR_YEAR_Q1 = 79
    RANGE_TYPE_NEXT_CALENDAR_YEAR_Q2 = 80
    RANGE_TYPE_NEXT_CALENDAR_YEAR_Q3 = 81
    RANGE_TYPE_NEXT_CALENDAR_YEAR_Q4 = 82

    RANGE_TYPE_CHOICES = (
        (RANGE_TYPE_LAST_36_MONTHS, 'Last 36 months'),
        (RANGE_TYPE_LAST_24_MONTHS, 'Last 24 months'),
        (RANGE_TYPE_LAST_18_MONTHS, 'Last 18 months'),
        (RANGE_TYPE_LAST_12_MONTHS, 'Last 12 months'),
        (RANGE_TYPE_LAST_6_MONTHS, 'Last 6 months'),
        (RANGE_TYPE_LAST_3_MONTHS, 'Last 3 months'),
        (RANGE_TYPE_LAST_90_DAYS, 'Last 90 days'),
        (RANGE_TYPE_LAST_2_MONTHS, 'Last 2 months'),
        (RANGE_TYPE_LAST_60_DAYS, 'Last 60 days'),
        (RANGE_TYPE_LAST_MONTH, 'Last month'),
        (RANGE_TYPE_LAST_28_DAYS, 'Last 28 days'),
        (RANGE_TYPE_LAST_14_DAYS, 'Last 14 days'),
        (RANGE_TYPE_LAST_7_DAYS, 'Last 7 days'),
        (RANGE_TYPE_6_WEEKS_AGO, '6 weeks ago'),
        (RANGE_TYPE_5_WEEKS_AGO, '5 weeks ago'),
        (RANGE_TYPE_4_WEEKS_AGO, '4 weeks ago'),
        (RANGE_TYPE_3_WEEKS_AGO, '3 weeks ago'),
        (RANGE_TYPE_2_WEEKS_AGO, '2 weeks ago'),
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
        (RANGE_TYPE_NEXT_2_MONTHS, 'Next 2 months'),
        (RANGE_TYPE_NEXT_60_DAYS, 'Next 60 days'),
        (RANGE_TYPE_NEXT_3_MONTHS, 'Next 3 months'),
        (RANGE_TYPE_NEXT_90_DAYS, 'Next 90 days'),
        (RANGE_TYPE_NEXT_6_MONTHS, 'Next 6 months'),
        (RANGE_TYPE_NEXT_12_MONTHS, 'Next 12 months'),
        (RANGE_TYPE_NEXT_24_MONTHS, 'Next 24 months'),
        (RANGE_TYPE_NEXT_36_MONTHS, 'Next 36 months'),
        # Financial year full ranges
        (RANGE_TYPE_LAST_FINANCIAL_YEAR, 'Last financial year'),
        (RANGE_TYPE_THIS_FINANCIAL_YEAR, 'This financial year'),
        (RANGE_TYPE_NEXT_FINANCIAL_YEAR, 'Next financial year'),
        # Last FY quarters
        (RANGE_TYPE_LAST_FINANCIAL_YEAR_Q1, 'Last financial year Q1'),
        (RANGE_TYPE_LAST_FINANCIAL_YEAR_Q2, 'Last financial year Q2'),
        (RANGE_TYPE_LAST_FINANCIAL_YEAR_Q3, 'Last financial year Q3'),
        (RANGE_TYPE_LAST_FINANCIAL_YEAR_Q4, 'Last financial year Q4'),
        # This FY quarters
        (RANGE_TYPE_THIS_FINANCIAL_YEAR_Q1, 'This financial year Q1'),
        (RANGE_TYPE_THIS_FINANCIAL_YEAR_Q2, 'This financial year Q2'),
        (RANGE_TYPE_THIS_FINANCIAL_YEAR_Q3, 'This financial year Q3'),
        (RANGE_TYPE_THIS_FINANCIAL_YEAR_Q4, 'This financial year Q4'),
        # Next FY quarters
        (RANGE_TYPE_NEXT_FINANCIAL_YEAR_Q1, 'Next financial year Q1'),
        (RANGE_TYPE_NEXT_FINANCIAL_YEAR_Q2, 'Next financial year Q2'),
        (RANGE_TYPE_NEXT_FINANCIAL_YEAR_Q3, 'Next financial year Q3'),
        (RANGE_TYPE_NEXT_FINANCIAL_YEAR_Q4, 'Next financial year Q4'),
        # Current FY quarters
        (RANGE_TYPE_LAST_FINANCIAL_QUARTER, 'Last financial quarter'),
        (RANGE_TYPE_CURRENT_FINANCIAL_QUARTER, 'Current financial quarter'),
        (RANGE_TYPE_NEXT_FINANCIAL_QUARTER, 'Next financial quarter'),
        (RANGE_TYPE_LAST_YEAR_SAME_FINANCIAL_QUARTER, 'Same quarter last financial year'),
        # Calendar year full ranges
        (RANGE_TYPE_LAST_CALENDAR_QUARTER, 'Last calendar quarter'),
        (RANGE_TYPE_THIS_CALENDAR_QUARTER, 'This calendar quarter'),
        (RANGE_TYPE_NEXT_CALENDAR_QUARTER, 'Next calendar quarter'),
        # Last calendar year quarters
        (RANGE_TYPE_LAST_CALENDAR_YEAR_Q1, 'Last calendar year Q1'),
        (RANGE_TYPE_LAST_CALENDAR_YEAR_Q2, 'Last calendar year Q2'),
        (RANGE_TYPE_LAST_CALENDAR_YEAR_Q3, 'Last calendar year Q3'),
        (RANGE_TYPE_LAST_CALENDAR_YEAR_Q4, 'Last calendar year Q4'),
        # This calendar year quarters
        (RANGE_TYPE_THIS_CALENDAR_YEAR_Q1, 'This calendar year Q1'),
        (RANGE_TYPE_THIS_CALENDAR_YEAR_Q2, 'This calendar year Q2'),
        (RANGE_TYPE_THIS_CALENDAR_YEAR_Q3, 'This calendar year Q3'),
        (RANGE_TYPE_THIS_CALENDAR_YEAR_Q4, 'This calendar year Q4'),
        # Next calendar year quarters
        (RANGE_TYPE_NEXT_CALENDAR_YEAR_Q1, 'Next calendar year Q1'),
        (RANGE_TYPE_NEXT_CALENDAR_YEAR_Q2, 'Next calendar year Q2'),
        (RANGE_TYPE_NEXT_CALENDAR_YEAR_Q3, 'Next calendar year Q3'),
        (RANGE_TYPE_NEXT_CALENDAR_YEAR_Q4, 'Next calendar year Q4'),
    )

    def get_variable_dates(self, range_type, financial_year_start_month=1):  # financial_year_start_month 1=jan
        today = date.today()
        start_of_this_week = today - timedelta(days=today.weekday())
        number_of_days = None
        if range_type == self.RANGE_TYPE_TODAY:
            start_date = today
            end_date = start_date
            number_of_days = 1
        elif range_type == self.RANGE_TYPE_YESTERDAY:  # Yesterday
            start_date = today - timedelta(days=1)
            end_date = start_date
            number_of_days = 1
        elif range_type == self.RANGE_TYPE_TOMORROW:  # Tomorrow
            start_date = today + timedelta(days=1)
            end_date = start_date
            number_of_days = 1
        elif range_type == self.RANGE_TYPE_THIS_WEEK:  # This Week
            start_date = start_of_this_week
            end_date = start_date + timedelta(days=6)
            number_of_days = 7
        elif range_type == self.RANGE_TYPE_NEXT_WEEK:  # Next Week
            start_date = start_of_this_week + timedelta(days=7)
            end_date = start_date + timedelta(days=6)
            number_of_days = 7
        elif range_type == self.RANGE_TYPE_LAST_WEEK:  # Last Week
            start_date = start_of_this_week - timedelta(days=7)
            end_date = start_date + timedelta(days=6)
            number_of_days = 7
        elif range_type == self.RANGE_TYPE_2_WEEKS_TIME:  # 2 Weeks Time
            start_date = start_of_this_week + timedelta(days=14)
            end_date = start_date + timedelta(days=6)
            number_of_days = 7
        elif range_type == self.RANGE_TYPE_2_WEEKS_AGO:  # 2 Weeks Ago
            start_date = start_of_this_week - timedelta(days=14)
            end_date = start_date + timedelta(days=6)
            number_of_days = 7
        elif range_type == self.RANGE_TYPE_3_WEEKS_TIME:  # 3 Weeks Time
            start_date = start_of_this_week + timedelta(days=21)
            end_date = start_date + timedelta(days=6)
            number_of_days = 7
        elif range_type == self.RANGE_TYPE_3_WEEKS_AGO:  # 3 Weeks Ago
            start_date = start_of_this_week - timedelta(days=21)
            end_date = start_date + timedelta(days=6)
            number_of_days = 7
        elif range_type == self.RANGE_TYPE_4_WEEKS_TIME:  # 4 Weeks Time
            start_date = start_of_this_week + timedelta(days=28)
            end_date = start_date + timedelta(days=6)
            number_of_days = 7
        elif range_type == self.RANGE_TYPE_4_WEEKS_AGO:  # 4 Weeks Ago
            start_date = start_of_this_week - timedelta(days=28)
            end_date = start_date + timedelta(days=6)
            number_of_days = 7
        elif range_type == self.RANGE_TYPE_5_WEEKS_TIME:  # 5 Weeks Time
            start_date = start_of_this_week + timedelta(days=35)
            end_date = start_date + timedelta(days=6)
            number_of_days = 7
        elif range_type == self.RANGE_TYPE_5_WEEKS_AGO:  # 5 Weeks Ago
            start_date = start_of_this_week - timedelta(days=35)
            end_date = start_date + timedelta(days=6)
            number_of_days = 7
        elif range_type == self.RANGE_TYPE_6_WEEKS_TIME:  # 6 Weeks Time
            start_date = start_of_this_week + timedelta(days=42)
            end_date = start_date + timedelta(days=6)
            number_of_days = 7
        elif range_type == self.RANGE_TYPE_6_WEEKS_AGO:  # 6 Weeks Ago
            start_date = start_of_this_week - timedelta(days=42)
            end_date = start_date + timedelta(days=6)
            number_of_days = 7
        elif range_type == self.RANGE_TYPE_THIS_MONTH:  # This Month
            start_date = date(today.year, today.month, 1)
            number_of_days = monthrange(today.year, today.month)[1]
            end_date = start_date + timedelta(days=number_of_days - 1)
        elif range_type == self.RANGE_TYPE_NEXT_MONTH:  # Next Month
            number_of_days_in_this_month = monthrange(today.year, today.month)[1]
            start_date = date(today.year, today.month, 1) + timedelta(days=number_of_days_in_this_month)
            number_of_days = monthrange(start_date.year, start_date.month)[1]
            end_date = start_date + timedelta(days=number_of_days - 1)
        elif range_type == self.RANGE_TYPE_LAST_MONTH:  # Last Month
            end_date = date(today.year, today.month, 1) - timedelta(days=1)
            last_month = end_date
            start_date = date(last_month.year, last_month.month, 1)
        elif range_type == self.RANGE_TYPE_NEXT_7_DAYS:  # Next 7 Days
            start_date = today
            end_date = start_date + timedelta(days=6)
            number_of_days = 7
        elif range_type == self.RANGE_TYPE_LAST_7_DAYS:  # Last 7 Days
            start_date = today - timedelta(days=6)
            end_date = today
            number_of_days = 7
        elif range_type == self.RANGE_TYPE_NEXT_14_DAYS:  # Next 14 Days
            start_date = today
            end_date = start_date + timedelta(days=14 - 1)
            number_of_days = 14
        elif range_type == self.RANGE_TYPE_LAST_14_DAYS:  # Last 14 Days
            start_date = today - timedelta(days=14 - 1)
            end_date = today
            number_of_days = 14
        elif range_type == self.RANGE_TYPE_NEXT_28_DAYS:  # Next 28 Days
            start_date = today
            end_date = start_date + timedelta(days=28 - 1)
            number_of_days = 28
        elif range_type == self.RANGE_TYPE_LAST_28_DAYS:  # Last 28 Days
            start_date = today - timedelta(days=28 - 1)
            end_date = today
            number_of_days = 28
        elif range_type == self.RANGE_TYPE_NEXT_60_DAYS:  # Next 60 Days
            start_date = today
            end_date = start_date + timedelta(days=60 - 1)
            number_of_days = 60
        elif range_type == self.RANGE_TYPE_LAST_60_DAYS:  # Last 60 Days
            start_date = today - timedelta(days=60 - 1)
            end_date = today
            number_of_days = 60
        elif range_type == self.RANGE_TYPE_NEXT_90_DAYS:  # Next 90 Days
            start_date = today
            end_date = start_date + timedelta(days=90 - 1)
            number_of_days = 90
        elif range_type == self.RANGE_TYPE_LAST_90_DAYS:  # Last 90 Days
            start_date = today - timedelta(days=90 - 1)
            end_date = today
            number_of_days = 90
        elif range_type == self.RANGE_TYPE_THIS_YEAR:  # This Year
            start_date = date(today.year, 1, 1)
            end_date = date(today.year, 12, 31)
        elif range_type == self.RANGE_TYPE_LAST_YEAR:  # Last Year
            last_year = today.year - 1
            start_date = date(last_year, 1, 1)
            end_date = date(last_year, 12, 31)
        elif range_type == self.RANGE_TYPE_LAST_18_MONTHS:
            date_offset = DateOffset()
            start_date = date_offset.get_offset('-18m', today)
            end_date = today
        elif range_type == self.RANGE_TYPE_LAST_2_MONTHS:
            date_offset = DateOffset()
            start_date = date_offset.get_offset('-2m', today)
            end_date = today
        elif range_type == self.RANGE_TYPE_NEXT_2_MONTHS:
            date_offset = DateOffset()
            start_date = today
            end_date = date_offset.get_offset('2m', today)
        elif range_type == self.RANGE_TYPE_LAST_3_MONTHS:
            date_offset = DateOffset()
            start_date = date_offset.get_offset('-3m', today)
            end_date = today
        elif range_type == self.RANGE_TYPE_NEXT_3_MONTHS:
            date_offset = DateOffset()
            start_date = today
            end_date = date_offset.get_offset('3m', today)
        elif range_type == self.RANGE_TYPE_LAST_6_MONTHS:
            date_offset = DateOffset()
            start_date = date_offset.get_offset('-6m', today)
            end_date = today
        elif range_type == self.RANGE_TYPE_NEXT_6_MONTHS:
            date_offset = DateOffset()
            start_date = today
            end_date = date_offset.get_offset('6m', today)
        elif range_type == self.RANGE_TYPE_LAST_12_MONTHS:
            date_offset = DateOffset()
            start_date = date_offset.get_offset('-12m', today)
            end_date = today
        elif range_type == self.RANGE_TYPE_NEXT_12_MONTHS:
            date_offset = DateOffset()
            start_date = today
            end_date = date_offset.get_offset('12m', today)
        elif range_type == self.RANGE_TYPE_LAST_24_MONTHS:
            date_offset = DateOffset()
            start_date = date_offset.get_offset('-24m', today)
            end_date = today
        elif range_type == self.RANGE_TYPE_NEXT_24_MONTHS:
            date_offset = DateOffset()
            start_date = today
            end_date = date_offset.get_offset('24m', today)
        elif range_type == self.RANGE_TYPE_LAST_36_MONTHS:
            date_offset = DateOffset()
            start_date = date_offset.get_offset('-36m', today)
            end_date = today
        elif range_type == self.RANGE_TYPE_NEXT_36_MONTHS:
            date_offset = DateOffset()
            start_date = today
            end_date = date_offset.get_offset('36m', today)
        elif range_type == self.RANGE_TYPE_LAST_FINANCIAL_YEAR:
            fy_year = self.get_fy_start_year(today, financial_year_start_month, offset=-1)
            start_date, end_date = self._get_financial_year_bounds(fy_year, financial_year_start_month)

        elif range_type == self.RANGE_TYPE_THIS_FINANCIAL_YEAR:
            fy_year = self.get_fy_start_year(today, financial_year_start_month, offset=0)
            start_date, end_date = self._get_financial_year_bounds(fy_year, financial_year_start_month)

        elif range_type == self.RANGE_TYPE_NEXT_FINANCIAL_YEAR:
            fy_year = self.get_fy_start_year(today, financial_year_start_month, offset=1)
            start_date, end_date = self._get_financial_year_bounds(fy_year, financial_year_start_month)

        elif range_type == self.RANGE_TYPE_LAST_FINANCIAL_YEAR_Q1:
            fy_year = self.get_fy_start_year(today, financial_year_start_month, offset=-1)
            fy_start, _ = self._get_financial_year_bounds(fy_year, financial_year_start_month)
            start_date, end_date = self._get_financial_quarter_bounds(fy_start, 1)

        elif range_type == self.RANGE_TYPE_LAST_FINANCIAL_YEAR_Q2:
            fy_year = self.get_fy_start_year(today, financial_year_start_month, offset=-1)
            fy_start, _ = self._get_financial_year_bounds(fy_year, financial_year_start_month)
            start_date, end_date = self._get_financial_quarter_bounds(fy_start, 2)

        elif range_type == self.RANGE_TYPE_LAST_FINANCIAL_YEAR_Q3:
            fy_year = self.get_fy_start_year(today, financial_year_start_month, offset=-1)
            fy_start, _ = self._get_financial_year_bounds(fy_year, financial_year_start_month)
            start_date, end_date = self._get_financial_quarter_bounds(fy_start, 3)

        elif range_type == self.RANGE_TYPE_LAST_FINANCIAL_YEAR_Q4:
            fy_year = self.get_fy_start_year(today, financial_year_start_month, offset=-1)
            fy_start, _ = self._get_financial_year_bounds(fy_year, financial_year_start_month)
            start_date, end_date = self._get_financial_quarter_bounds(fy_start, 4)

        elif range_type == self.RANGE_TYPE_THIS_FINANCIAL_YEAR_Q1:
            fy_year = self.get_fy_start_year(today, financial_year_start_month, offset=0)
            fy_start, _ = self._get_financial_year_bounds(fy_year, financial_year_start_month)
            start_date, end_date = self._get_financial_quarter_bounds(fy_start, 1)

        elif range_type == self.RANGE_TYPE_THIS_FINANCIAL_YEAR_Q2:
            fy_year = self.get_fy_start_year(today, financial_year_start_month, offset=0)
            fy_start, _ = self._get_financial_year_bounds(fy_year, financial_year_start_month)
            start_date, end_date = self._get_financial_quarter_bounds(fy_start, 2)

        elif range_type == self.RANGE_TYPE_THIS_FINANCIAL_YEAR_Q3:
            fy_year = self.get_fy_start_year(today, financial_year_start_month, offset=0)
            fy_start, _ = self._get_financial_year_bounds(fy_year, financial_year_start_month)
            start_date, end_date = self._get_financial_quarter_bounds(fy_start, 3)

        elif range_type == self.RANGE_TYPE_THIS_FINANCIAL_YEAR_Q4:
            fy_year = self.get_fy_start_year(today, financial_year_start_month, offset=0)
            fy_start, _ = self._get_financial_year_bounds(fy_year, financial_year_start_month)
            start_date, end_date = self._get_financial_quarter_bounds(fy_start, 4)

        elif range_type == self.RANGE_TYPE_NEXT_FINANCIAL_YEAR_Q1:
            fy_year = self.get_fy_start_year(today, financial_year_start_month, offset=1)
            fy_start, _ = self._get_financial_year_bounds(fy_year, financial_year_start_month)
            start_date, end_date = self._get_financial_quarter_bounds(fy_start, 1)

        elif range_type == self.RANGE_TYPE_NEXT_FINANCIAL_YEAR_Q2:
            fy_year = self.get_fy_start_year(today, financial_year_start_month, offset=1)
            fy_start, _ = self._get_financial_year_bounds(fy_year, financial_year_start_month)
            start_date, end_date = self._get_financial_quarter_bounds(fy_start, 2)

        elif range_type == self.RANGE_TYPE_NEXT_FINANCIAL_YEAR_Q3:
            fy_year = self.get_fy_start_year(today, financial_year_start_month, offset=1)
            fy_start, _ = self._get_financial_year_bounds(fy_year, financial_year_start_month)
            start_date, end_date = self._get_financial_quarter_bounds(fy_start, 3)

        elif range_type == self.RANGE_TYPE_NEXT_FINANCIAL_YEAR_Q4:
            fy_year = self.get_fy_start_year(today, financial_year_start_month, offset=1)
            fy_start, _ = self._get_financial_year_bounds(fy_year, financial_year_start_month)
            start_date, end_date = self._get_financial_quarter_bounds(fy_start, 4)

        elif range_type == self.RANGE_TYPE_LAST_FINANCIAL_QUARTER:
            fy_year, quarter = self._get_current_fy_quarter(today, financial_year_start_month)

            # Move back one quarter
            if quarter == 1:
                quarter = 4
                fy_year -= 1
            else:
                quarter -= 1

            fy_start, _ = self._get_financial_year_bounds(fy_year, financial_year_start_month)
            start_date, end_date = self._get_financial_quarter_bounds(fy_start, quarter)

        elif range_type == self.RANGE_TYPE_CURRENT_FINANCIAL_QUARTER:
            fy_year, quarter = self._get_current_fy_quarter(today, financial_year_start_month)

            fy_start, _ = self._get_financial_year_bounds(fy_year, financial_year_start_month)
            start_date, end_date = self._get_financial_quarter_bounds(fy_start, quarter)

        elif range_type == self.RANGE_TYPE_NEXT_FINANCIAL_QUARTER:
            fy_year, quarter = self._get_current_fy_quarter(today, financial_year_start_month)

            # Move forward one quarter
            if quarter == 4:
                quarter = 1
                fy_year += 1
            else:
                quarter += 1

            fy_start, _ = self._get_financial_year_bounds(fy_year, financial_year_start_month)
            start_date, end_date = self._get_financial_quarter_bounds(fy_start, quarter)

        elif range_type == self.RANGE_TYPE_LAST_YEAR_SAME_FINANCIAL_QUARTER:
            # Determine current quarter in THIS FY
            this_fy_year, current_quarter = self._get_current_fy_quarter(today, financial_year_start_month)

            # Move back one FY but keep same quarter number
            fy_year = this_fy_year - 1

            fy_start, _ = self._get_financial_year_bounds(fy_year, financial_year_start_month)
            start_date, end_date = self._get_financial_quarter_bounds(fy_start, current_quarter)

        elif range_type == self.RANGE_TYPE_LAST_CALENDAR_QUARTER:
            # Current calendar quarter
            quarter = self._get_calendar_quarter(today)
            year = today.year

            # Move back one quarter
            if quarter == 1:
                quarter = 4
                year -= 1
            else:
                quarter -= 1

            start_date, end_date = self._get_calendar_quarter_bounds(year, quarter)

        elif range_type == self.RANGE_TYPE_THIS_CALENDAR_QUARTER:
            quarter = self._get_calendar_quarter(today)
            year = today.year

            start_date, end_date = self._get_calendar_quarter_bounds(year, quarter)

        elif range_type == self.RANGE_TYPE_NEXT_CALENDAR_QUARTER:
            quarter = self._get_calendar_quarter(today)
            year = today.year

            # Move forward one quarter
            if quarter == 4:
                quarter = 1
                year += 1
            else:
                quarter += 1

            start_date, end_date = self._get_calendar_quarter_bounds(year, quarter)

        elif range_type == self.RANGE_TYPE_LAST_CALENDAR_YEAR_Q1:
            year = today.year - 1
            start_date, end_date = self._get_calendar_quarter_bounds(year, 1)

        elif range_type == self.RANGE_TYPE_LAST_CALENDAR_YEAR_Q2:
            year = today.year - 1
            start_date, end_date = self._get_calendar_quarter_bounds(year, 2)

        elif range_type == self.RANGE_TYPE_LAST_CALENDAR_YEAR_Q3:
            year = today.year - 1
            start_date, end_date = self._get_calendar_quarter_bounds(year, 3)

        elif range_type == self.RANGE_TYPE_LAST_CALENDAR_YEAR_Q4:
            year = today.year - 1
            start_date, end_date = self._get_calendar_quarter_bounds(year, 4)

        elif range_type == self.RANGE_TYPE_THIS_CALENDAR_YEAR_Q1:
            year = today.year
            start_date, end_date = self._get_calendar_quarter_bounds(year, 1)

        elif range_type == self.RANGE_TYPE_THIS_CALENDAR_YEAR_Q2:
            year = today.year
            start_date, end_date = self._get_calendar_quarter_bounds(year, 2)

        elif range_type == self.RANGE_TYPE_THIS_CALENDAR_YEAR_Q3:
            year = today.year
            start_date, end_date = self._get_calendar_quarter_bounds(year, 3)

        elif range_type == self.RANGE_TYPE_THIS_CALENDAR_YEAR_Q4:
            year = today.year
            start_date, end_date = self._get_calendar_quarter_bounds(year, 4)

        elif range_type == self.RANGE_TYPE_NEXT_CALENDAR_YEAR_Q1:
            year = today.year + 1
            start_date, end_date = self._get_calendar_quarter_bounds(year, 1)

        elif range_type == self.RANGE_TYPE_NEXT_CALENDAR_YEAR_Q2:
            year = today.year + 1
            start_date, end_date = self._get_calendar_quarter_bounds(year, 2)

        elif range_type == self.RANGE_TYPE_NEXT_CALENDAR_YEAR_Q3:
            year = today.year + 1
            start_date, end_date = self._get_calendar_quarter_bounds(year, 3)

        elif range_type == self.RANGE_TYPE_NEXT_CALENDAR_YEAR_Q4:
            year = today.year + 1
            start_date, end_date = self._get_calendar_quarter_bounds(year, 4)

        else:
            raise AssertionError('unknown date value')
        if number_of_days is None:
            number_of_days = (end_date - start_date).days + 1
        start_date_and_time = datetime.combine(start_date, datetime.min.time())
        end_date_and_time = datetime.combine(end_date, datetime.max.time())

        return start_date_and_time, end_date_and_time, number_of_days

    def get_variable_date_filter_values(self):
        values = {}
        for choice in self.RANGE_TYPE_CHOICES:
            values['#variable_date:%d' % choice[0]] = choice[1]
        return values

    @staticmethod
    def get_date_filter_years():
        values = {}
        today = date.today()
        start_year = today.year - 15
        end_year = start_year + 20

        for year in range(start_year, end_year):
            values['#year:%d' % year] = year
        return values

    @staticmethod
    def get_date_filter_months():
        values = {}
        for index, month in enumerate(list(calendar.month_name)[1:], 1):
            values['#month:%d' % index] = month
        return values

    @staticmethod
    def get_date_filter_quarters():
        values = {}
        for quarter in range(1, 5):
            values['#quarter:%d' % quarter] = f'Quarter {quarter}'
        for quarter in range(1, 5):
            values['#financial_quarter:%d' % quarter] = f'Financial Quarter {quarter}'
        return values

    @staticmethod
    def get_fy_start_year(today, fy_start_month, offset=0):
        """
        Returns the start year of the financial year.
        offset = -1 (last FY), 0 (this FY), +1 (next FY)
        """
        this_fy_start_year = today.year if today.month >= fy_start_month else today.year - 1
        return this_fy_start_year + offset

    @staticmethod
    def _get_financial_year_bounds(year, start_month):
        """
        Returns inclusive financial year date range:
        start_date, end_date
        """
        start = date(year, start_month, 1)

        # start of next FY
        next_start = date(year + 1, 1, 1) if start_month == 1 else date(year + 1, start_month, 1)

        end = next_start - timedelta(days=1)
        return start, end

    @staticmethod
    def _get_financial_quarter_bounds(fy_start_date, quarter_number):
        """
        Returns inclusive quarter range inside a financial year.
        """
        q_start = fy_start_date + relativedelta(months=3 * (quarter_number - 1))
        q_end = q_start + relativedelta(months=3) - timedelta(days=1)
        return q_start, q_end

    def _get_current_fy_quarter(self, today, fy_start_month):
        # Get start of this FY
        fy_year = self.get_fy_start_year(today, fy_start_month, offset=0)
        fy_start, _ = self._get_financial_year_bounds(fy_year, fy_start_month)

        # Months difference from FY start
        delta_months = (today.year - fy_start.year) * 12 + (today.month - fy_start.month)

        # Quarter index (0,1,2,3)
        quarter = delta_months // 3 + 1
        return fy_year, quarter

    @staticmethod
    def _get_calendar_quarter(dt):
        return (dt.month - 1) // 3 + 1

    def _get_calendar_quarter_bounds(self, year, quarter):
        """
        Calendar quarter is simply a financial quarter where FY starts in January.
        """
        fy_start_date = date(year, 1, 1)
        return self._get_financial_quarter_bounds(fy_start_date, quarter)
