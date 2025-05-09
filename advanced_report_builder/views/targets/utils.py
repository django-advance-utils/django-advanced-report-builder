from calendar import monthrange

from django.utils.dates import MONTHS


def get_target_value(min_date, max_date, target, month_range=False):
    override_data = target.get_override_data()

    # We could find the proportion of the start month and end_month
    # we are interested in and multiply the target by the result.

    if min_date and max_date and override_data:
        start_month = min_date.month
        end_month = max_date.month
        total_target_value = 0

        if month_range:
            # if we know that the range is exactly a month long then we can just look it up in the dict.
            for year in range(min_date.year, max_date.year + 1):
                year_data = override_data.get(str(year))

                if year_data:
                    month_str = MONTHS.get(min_date.month)
                    return year_data.get(month_str, target.get_value())
                else:
                    return target.get_value()
        else:
            # if it isn't exactly a month long, then we need to do some calculations to find the exact amount.

            for year in range(min_date.year, max_date.year + 1):
                year_data = override_data.get(str(year))
                yearly_target_value = 0

                for month in range(start_month, end_month + 1):
                    if year_data:
                        month_str = MONTHS.get(month)
                        month_value = year_data.get(month_str)
                    else:
                        month_value = target.get_value()

                    days_in_month = monthrange(year, month)[1]

                    # Work out the days inside the target in this month:
                    if (month == min_date.month and year == min_date.year) and (
                        month == max_date.month and year == max_date.year
                    ):
                        # if start and end dates are in the same month and year, just subtract min from max.
                        days_in_target = (max_date - min_date).days
                    elif month == min_date.month and year == min_date.year:
                        days_in_target = (days_in_month - min_date.day) + 1
                    elif month == max_date.month and year == max_date.year:
                        days_in_target = max_date.day
                    else:
                        days_in_target = days_in_month

                    # The actual target value for this month will have to be a proportion.
                    # (Since the start date might be after the 1st of the month
                    # and the end_date might be before the last day of the month.
                    target_in_month = (days_in_target / days_in_month) * month_value
                    yearly_target_value += target_in_month

                total_target_value += yearly_target_value

        return total_target_value
    else:
        # we don't have any dates to compare against, so we can only use the monthly default value.
        return target.get_value()
