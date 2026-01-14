from calendar import monthrange
from datetime import date, timedelta

from django.utils.dates import MONTHS

from advanced_report_builder.models import Target


class TargetUtils:
    @staticmethod
    def is_exact_full_month(min_date: date, max_date: date) -> bool:
        if min_date.year != max_date.year or min_date.month != max_date.month:
            return False

        if min_date.day != 1:
            return False

        last_day = monthrange(min_date.year, min_date.month)[1]
        return max_date.day == last_day

    def get_monthly_target_value_for_range(self, min_date, max_date, target):
        """
        Returns the monthly target value for an arbitrary date range.

        Rules:
        - Exact full calendar month → direct lookup
        - Partial / multi-month range → prorated by days
        """

        # Safety fallback
        if not min_date or not max_date:
            return target.get_value()

        override_data = target.get_override_data() or {}

        # ---- 1. Exact full month → lookup only ----
        if self.is_exact_full_month(min_date, max_date):
            year_data = override_data.get(str(min_date.year))
            if year_data:
                month_str = MONTHS[min_date.month]
                return year_data.get(month_str, target.get_value())
            return target.get_value()

        # ---- 2. Partial / multi-month → prorated ----
        total = 0.0

        current = date(min_date.year, min_date.month, 1)

        while current <= max_date:
            year = current.year
            month = current.month

            days_in_month = monthrange(year, month)[1]
            month_start = date(year, month, 1)
            month_end = date(year, month, days_in_month)

            effective_start = max(min_date, month_start)
            effective_end = min(max_date, month_end)

            if effective_start <= effective_end:
                days_in_range = (effective_end - effective_start).days + 1

                year_data = override_data.get(str(year), {})
                month_str = MONTHS[month]
                month_value = year_data.get(month_str, target.get_value())

                total += (days_in_range / days_in_month) * month_value

            # advance month
            current = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)

        return total

    @staticmethod
    def start_of_week(d: date) -> date:
        return d - timedelta(days=d.weekday())

    def is_exact_full_week(self, min_date: date, max_date: date) -> bool:
        week_start = self.start_of_week(min_date)
        week_end = week_start + timedelta(days=6)

        return min_date == week_start and max_date == week_end

    def get_weekly_target_value_for_range(self, min_date, max_date, target):
        """
        Returns the weekly target value for an arbitrary date range.

        Rules:
        - Exact full week → direct lookup
        - Partial / multi-week range → prorated by days
        """

        # Safety fallback
        if not min_date or not max_date:
            return target.get_value()

        override_data = target.get_override_data() or {}

        # ---- 1. Exact full week → lookup ----
        if self.is_exact_full_week(min_date, max_date):
            year, week_no, _ = min_date.isocalendar()
            year_data = override_data.get(str(year))
            if year_data:
                week_key = f'W{week_no:02d}'
                return year_data.get(week_key, target.get_value())
            return target.get_value()

        # ---- 2. Partial / multi-week → prorated ----
        total = 0.0
        current = self.start_of_week(min_date)

        while current <= max_date:
            week_start = current
            week_end = week_start + timedelta(days=6)

            effective_start = max(min_date, week_start)
            effective_end = min(max_date, week_end)

            if effective_start <= effective_end:
                days_in_range = (effective_end - effective_start).days + 1

                year, week_no, _ = week_start.isocalendar()
                year_data = override_data.get(str(year), {})
                week_key = f'W{week_no:02d}'

                week_value = year_data.get(week_key, target.get_value())

                total += (days_in_range / 7) * week_value

            current += timedelta(days=7)

        return total

    @staticmethod
    def get_daily_target_value_for_range(min_date, max_date, target):
        """
        Returns the daily target value for an arbitrary date range.

        Rules:
        - Each day contributes exactly one daily target value
        - Overrides are applied per day if present
        """

        # Safety fallback
        if not min_date or not max_date:
            return target.get_value()

        override_data = target.get_override_data() or {}
        default_value = target.get_value()

        total = 0.0
        current = min_date

        while current <= max_date:
            year_data = override_data.get(str(current.year), {})

            # Support either YYYY-MM-DD or day-of-year style keys
            day_key = current.isoformat()  # "2025-03-12"
            doy_key = f'D{current.timetuple().tm_yday:03d}'  # "D071"

            day_value = year_data.get(day_key) or year_data.get(doy_key) or default_value

            total += day_value
            current += timedelta(days=1)

        return total

    @staticmethod
    def get_quarterly_target_value_for_range(min_date, target):
        """
        Return the quarterly target value.
        Quarter validity is assumed to be checked by the caller.
        """

        override_data = target.get_override_data() or {}

        year = min_date.year
        quarter = ((min_date.month - 1) // 3) + 1
        quarter_key = f'Q{quarter}'

        year_data = override_data.get(str(year))
        if year_data and quarter_key in year_data:
            return year_data[quarter_key]

        return target.get_value()

    @staticmethod
    def get_yearly_target_value_for_range(min_date, target):
        override_data = target.get_override_data() or {}

        year_data = override_data.get(str(min_date.year))
        if year_data and 'YEAR' in year_data:
            return year_data['YEAR']

        return target.get_value()

    def get_target_value(self, period_data, target):
        if target.period_type == Target.PeriodType.DAILY:
            period = period_data.get_day_period()
            if period is None:
                return None
            target_value = self.get_daily_target_value_for_range(
                min_date=period[0],
                max_date=period[1],
                target=target,
            )

        elif target.period_type == Target.PeriodType.WEEKLY:
            period = period_data.get_week_period()
            if period is None:
                return None
            target_value = self.get_weekly_target_value_for_range(
                min_date=period[0],
                max_date=period[1],
                target=target,
            )

        elif target.period_type == Target.PeriodType.MONTHLY:
            period = period_data.get_month_period()
            if period is None:
                return None
            target_value = self.get_monthly_target_value_for_range(
                min_date=period[0],
                max_date=period[1],
                target=target,
            )

        elif target.period_type == Target.PeriodType.QUARTER:
            period = period_data.get_quarter_period()
            if period is None:
                return None
            target_value = self.get_quarterly_target_value_for_range(
                min_date=period[0],
                target=target,
            )
        elif target.period_type == Target.PeriodType.YEARLY:
            period = period_data.get_year_period()
            if period is None:
                return None

            target_value = self.get_yearly_target_value_for_range(
                min_date=period[0],
                target=target,
            )
        else:
            return None

        if target_value == 0:
            return None

        return target_value
