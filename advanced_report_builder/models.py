from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.dates import MONTHS
from django_datatables.columns import DatatableColumn, ManyToManyColumn, NoHeadingColumn
from django_datatables.model_def import DatatableModel
from django_modals.model_fields.colour import ColourField
from time_stamped_model.models import TimeStampedModel

from advanced_report_builder.globals import (
    ANNOTATION_CHART_SCALE,
    ANNOTATION_CHOICE_COUNT,
    ANNOTATION_VALUE_CHOICES,
    ANNOTATIONS_CHOICES,
    CALENDAR_VIEW_TYPE_CHOICES,
    CALENDAR_VIEW_TYPE_DAY,
    CALENDAR_VIEW_TYPE_GRID_WEEK,
    CALENDAR_VIEW_TYPE_LIST_WEEK,
    CALENDAR_VIEW_TYPE_MONTH,
    CALENDAR_VIEW_TYPE_YEAR,
    DISPLAY_OPTION_2_PER_ROW,
    DISPLAY_OPTION_CHOICES,
    DISPLAY_OPTION_CLASSES,
    DISPLAY_OPTION_NONE,
)
from advanced_report_builder.signals import model_report_save


class Target(TimeStampedModel):
    TARGET_TYPE_COUNT = 1
    TARGET_TYPE_MONEY = 2
    TARGET_TYPE_PERCENTAGE = 3

    TARGET_TYPE_CHOICES = (
        (TARGET_TYPE_COUNT, 'Count'),
        (TARGET_TYPE_MONEY, 'Money'),
        (TARGET_TYPE_PERCENTAGE, 'Percentage'),
    )

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=64)
    target_type = models.PositiveSmallIntegerField(choices=TARGET_TYPE_CHOICES)
    colour = ColourField(null=True, blank=True, help_text='The colour when it gets displayed on a report')
    default_value = models.IntegerField(blank=True, null=True)
    default_percentage = models.FloatField(blank=True, null=True)
    overridden = models.BooleanField(default=False)
    override_data = models.JSONField(null=True, blank=True)

    def get_value(self):
        if self.target_type == self.TARGET_TYPE_PERCENTAGE:
            return self.default_percentage
        return self.default_value

    def __str__(self):
        return self.name

    def get_override_data(self):
        override_data = self.override_data if self.override_data else {}

        ordered_value_dict = {}

        for year, data in override_data.items():
            if not ordered_value_dict.get(year):
                ordered_value_dict[year] = {}
            for month in MONTHS.values():
                if data.get(str(month)):
                    ordered_value_dict[year][month] = data[month]
                else:
                    ordered_value_dict[year][month] = self.default_value

        return ordered_value_dict

    def add_year(self, year):
        override_data = self.override_data if self.override_data else {}
        if not override_data.get(str(year)):
            override_data[str(year)] = {}
        temp = {}
        # Create a temp dict that has the keys as integers.
        for key, value in override_data.items():
            temp[int(key)] = value
        sorted_dict = {}
        for key in sorted(temp):
            sorted_dict[str(key)] = temp[key]
        if sorted_dict:
            self.override_data = sorted_dict
            self.save()

    def save(self, *args, **kwargs):
        """
        Overrides the save so that a new slug is generated
        :param args:
        :param kwargs:
        """
        self.make_new_slug()
        super().save(*args, **kwargs)


class ReportTag(TimeStampedModel):
    name = models.CharField(max_length=128, unique=True)
    slug = models.SlugField(unique=True)
    order = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ('order',)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.make_new_slug(allow_dashes=False, on_edit=True)
        self.set_order_field()
        return super().save(*args, **kwargs)


class ReportType(TimeStampedModel):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    content_type = models.ForeignKey(ContentType, null=False, blank=False, on_delete=models.PROTECT)
    report_builder_class_name = models.CharField(max_length=200)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        self.make_new_slug(allow_dashes=False, on_edit=True)
        return super().save(*args, **kwargs)


class Report(TimeStampedModel):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    slug_alias = models.SlugField(blank=True, null=True)  # used if the slug changes
    report_type = models.ForeignKey(ReportType, null=True, blank=False, on_delete=models.PROTECT)
    instance_type = models.CharField(null=True, max_length=255)
    report_tags = models.ManyToManyField(ReportTag, blank=True)
    notes = models.TextField(null=True, blank=True)
    version = models.PositiveSmallIntegerField(default=0)
    user_created = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='report_user_created_set',
    )
    user_updated = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='report_user_updated_set',
    )

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

    def get_report(self):
        return getattr(self, self.instance_type)

    def get_title(self):
        return self.name

    def save(self, *args, **kwargs):
        current_user = getattr(self, '_current_user', None)
        if current_user is not None and current_user.is_authenticated:
            self.user_updated = current_user
            if self.user_created is None:
                self.user_created = current_user
        is_new = self.pk is None
        if self.version is not None:
            self.version += 1
        slug_alias = self.slug
        self.make_new_slug(obj=Report, allow_dashes=False, on_edit=True)
        if slug_alias != self.slug:
            self.slug_alias = slug_alias
        if self.instance_type is None:
            self.instance_type = self._meta.label_lower.split('.')[1]
        result = super().save(*args, **kwargs)
        model_report_save.send(sender=self.__class__, instance=self, created=is_new, user=current_user)
        return result

    def get_base_model(self):
        return self.report_type.content_type.model_class()

    class Datatable(DatatableModel):
        class OutputType(DatatableColumn):
            output_types = {
                'tablereport': 'Table',
                'singlevaluereport': 'Single Value',
                'barchartreport': 'Bar Chart',
                'linechartreport': 'Line Chart',
                'piechartreport': 'Pie Chart',
                'funnelchartreport': 'Funnel Chart',
                'kanbanreport': 'Kanban',
                'customreport': 'Custom',
                'calendarreport': 'Calendar',
            }

            def col_setup(self):
                self.field = ['instance_type', 'customreport__output_type']

            # noinspection PyMethodMayBeStatic
            def row_result(self, data, _page_data):
                instance_type = data[self.model_path + 'instance_type']
                if instance_type == 'customreport':
                    output_type = data[self.model_path + 'customreport__output_type']
                    if output_type:
                        return output_type
                return self.output_types.get(instance_type, '')

        class OutputTypeIcon(NoHeadingColumn):
            output_types = {
                'tablereport': '<i class="fas fa-table"></i>',
                'singlevaluereport': '<i class="fas fa-box-open"></i>',
                'barchartreport': '<i class="fas fa-chart-bar"></i>',
                'linechartreport': '<i class="fas fa-chart-line"></i>',
                'piechartreport': '<i class="fas fa-chart-pie"></i>',
                'funnelchartreport': '<i class="fas fa-filter"></i>',
                'kanbanreport': '<i class="fas fa-chart-bar fa-flip-vertical"></i>',
                'customreport': '<i class="fas fa-file"></i>',
                'calendarreport': '<i class="fas fa-calendar"></i>',
            }

            def col_setup(self):
                self.field = ['instance_type']

            # noinspection PyMethodMayBeStatic
            def row_result(self, data, _page_data):
                instance_type = data[self.model_path + 'instance_type']
                return self.output_types.get(instance_type, '')

        report_tags_badge = ManyToManyColumn(
            field='report_tags__name',
            html='<span class="badge badge-primary"> %1% </span>',
            title='Tags',
        )


class ReportQuery(TimeStampedModel):
    report = models.ForeignKey(Report, on_delete=models.CASCADE)
    name = models.CharField(max_length=256, default='Standard')
    query = models.JSONField(null=True, blank=True)
    extra_query = models.JSONField(null=True, blank=True)  # used for single value Numerator
    order = models.PositiveSmallIntegerField()

    def save(self, *args, **kwargs):
        self.set_order_field(extra_filters={'report': self.report})
        result = super().save(*args, **kwargs)
        self.report._current_user = getattr(self, '_current_user', None)  # this is to update the users
        self.report.save()
        return result

    class Meta:
        ordering = ['order']
        verbose_name_plural = 'Report queries'

    def __str__(self):
        return self.name


class ReportQueryOrder(TimeStampedModel):
    report_query = models.ForeignKey(ReportQuery, on_delete=models.CASCADE)
    order_by_field = models.CharField(max_length=200, blank=True, null=True)
    order_by_ascending = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ['order']

    def save(self, *args, **kwargs):
        self.set_order_field(extra_filters={'report_query': self.report_query})
        return super().save(*args, **kwargs)


class TableReport(Report):
    table_fields = models.JSONField(null=True, blank=True)
    has_clickable_rows = models.BooleanField(default=False)
    link_field = models.CharField(max_length=200, blank=True, null=True)
    pivot_fields = models.JSONField(null=True, blank=True)
    order_by_field = models.CharField(max_length=200, blank=True, null=True)
    order_by_ascending = models.BooleanField(default=True)
    page_length = models.PositiveSmallIntegerField(
        choices=(
            (10, '10'),
            (25, '25'),
            (50, '50'),
            (100, '100'),
            (150, '150'),
            (200, '200'),
        ),
        default=100,
    )


class SingleValueReport(Report):
    SINGLE_VALUE_TYPE_COUNT = 1
    SINGLE_VALUE_TYPE_SUM = 2
    SINGLE_VALUE_TYPE_COUNT_AND_SUM = 3
    SINGLE_VALUE_TYPE_PERCENT = 4
    SINGLE_VALUE_TYPE_PERCENT_FROM_COUNT = 5
    SINGLE_VALUE_TYPE_AVERAGE_SUM_FROM_COUNT = 6
    SINGLE_VALUE_TYPE_AVERAGE_SUM_OVER_TIME = 7

    SINGLE_VALUE_TYPE_CHOICES = (
        (SINGLE_VALUE_TYPE_COUNT, 'Count'),
        (SINGLE_VALUE_TYPE_SUM, 'Sum'),
        (SINGLE_VALUE_TYPE_COUNT_AND_SUM, 'Count & Sum'),
        (SINGLE_VALUE_TYPE_PERCENT, 'Percent'),
        (SINGLE_VALUE_TYPE_PERCENT_FROM_COUNT, 'Percent from Count'),
        (SINGLE_VALUE_TYPE_AVERAGE_SUM_FROM_COUNT, 'Average Sum from Count'),
        (SINGLE_VALUE_TYPE_AVERAGE_SUM_OVER_TIME, 'Average Sum over Time'),
    )

    tile_colour = ColourField(blank=True, null=True)
    field = models.CharField(max_length=200, blank=True, null=True)  # denominator
    numerator = models.CharField(max_length=200, blank=True, null=True)
    single_value_type = models.PositiveSmallIntegerField(
        choices=SINGLE_VALUE_TYPE_CHOICES, default=SINGLE_VALUE_TYPE_COUNT
    )
    prefix = models.CharField(max_length=64, blank=True, null=True)
    decimal_places = models.IntegerField(default=0)
    show_breakdown = models.BooleanField(default=False)
    breakdown_fields = models.JSONField(null=True, blank=True)

    average_scale = models.PositiveSmallIntegerField(choices=ANNOTATION_VALUE_CHOICES, blank=True, null=True)
    average_start_period = models.PositiveSmallIntegerField(blank=True, null=True)
    average_end_period = models.PositiveSmallIntegerField(blank=True, null=True)

    def is_percentage(self):
        return self.single_value_type in [
            self.SINGLE_VALUE_TYPE_PERCENT,
            self.SINGLE_VALUE_TYPE_PERCENT_FROM_COUNT,
        ]


class BarChartReport(Report):
    BAR_CHART_ORIENTATION_VERTICAL = 1
    BAR_CHART_ORIENTATION_HORIZONTAL = 2

    BAR_CHART_ORIENTATION_CHOICES = (
        (BAR_CHART_ORIENTATION_VERTICAL, 'Vertical'),
        (BAR_CHART_ORIENTATION_HORIZONTAL, 'Horizontal'),
    )

    DATE_FIELD_SINGLE = 1
    DATE_FIELD_RANGE = 2

    DATE_FIELD_CHOICES = ((DATE_FIELD_SINGLE, 'Single'), (DATE_FIELD_RANGE, 'Range'))

    axis_scale = models.PositiveSmallIntegerField(choices=ANNOTATION_VALUE_CHOICES)

    date_field_type = models.PositiveSmallIntegerField(choices=DATE_FIELD_CHOICES, default=DATE_FIELD_SINGLE)

    date_field = models.CharField(max_length=200)
    end_date_field = models.CharField(max_length=200, blank=True, null=True)

    axis_value_type = models.PositiveSmallIntegerField(
        choices=ANNOTATIONS_CHOICES,
        default=ANNOTATION_CHOICE_COUNT,
        null=True,
        blank=True,
    )
    fields = models.JSONField(null=True, blank=True)
    x_label = models.CharField(max_length=200, blank=True, null=True)
    y_label = models.CharField(max_length=200, blank=True, null=True)

    bar_chart_orientation = models.PositiveSmallIntegerField(
        choices=BAR_CHART_ORIENTATION_CHOICES, default=BAR_CHART_ORIENTATION_VERTICAL
    )
    stacked = models.BooleanField(default=False)
    show_totals = models.BooleanField(default=False)
    show_blank_dates = models.BooleanField(default=True)

    show_breakdown = models.BooleanField(default=False)
    breakdown_fields = models.JSONField(null=True, blank=True)

    def is_orientation_vertical(self):
        return self.bar_chart_orientation == self.BAR_CHART_ORIENTATION_VERTICAL

    def get_chart_scale(self):
        return ANNOTATION_CHART_SCALE[self.axis_scale]


class LineChartReport(Report):
    axis_scale = models.PositiveSmallIntegerField(choices=ANNOTATION_VALUE_CHOICES)
    date_field = models.CharField(max_length=200)
    axis_value_type = models.PositiveSmallIntegerField(
        choices=ANNOTATIONS_CHOICES,
        default=ANNOTATION_CHOICE_COUNT,
        null=True,
        blank=True,
    )
    fields = models.JSONField(null=True, blank=True)
    x_label = models.CharField(max_length=200, blank=True, null=True)
    y_label = models.CharField(max_length=200, blank=True, null=True)
    show_totals = models.BooleanField(default=False)

    has_targets = models.BooleanField(default=False)
    targets = models.ManyToManyField(Target, blank=True)

    def get_chart_scale(self):
        return ANNOTATION_CHART_SCALE[self.axis_scale]


class PieChartReport(Report):
    PIE_CHART_STYLE_PIE = 1
    PIE_CHART_STYLE_DOUGHNUT = 2

    PIE_CHART_STYLE_CHOICES = (
        (PIE_CHART_STYLE_PIE, 'Pie'),
        (PIE_CHART_STYLE_DOUGHNUT, 'Doughnut'),
    )

    axis_value_type = models.PositiveSmallIntegerField(
        choices=ANNOTATIONS_CHOICES,
        default=ANNOTATION_CHOICE_COUNT,
        null=True,
        blank=True,
    )
    fields = models.JSONField(null=True, blank=True)
    style = models.PositiveSmallIntegerField(choices=PIE_CHART_STYLE_CHOICES, default=PIE_CHART_STYLE_PIE)

    def is_pie_chart(self):
        return self.style == self.PIE_CHART_STYLE_PIE


class FunnelChartReport(Report):
    axis_value_type = models.PositiveSmallIntegerField(
        choices=ANNOTATIONS_CHOICES,
        default=ANNOTATION_CHOICE_COUNT,
        null=True,
        blank=True,
    )
    fields = models.JSONField(null=True, blank=True)


class KanbanReport(Report):
    pass


class KanbanReportDescription(TimeStampedModel):
    kanban_report = models.ForeignKey(KanbanReport, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    report_type = models.ForeignKey(ReportType, null=True, blank=False, on_delete=models.PROTECT)
    description = models.TextField(blank=True, null=True)
    order = models.PositiveSmallIntegerField()

    def save(self, *args, **kwargs):
        self.set_order_field(extra_filters={'kanban_report': self.kanban_report})
        result = super().save(*args, **kwargs)
        self.kanban_report._current_user = getattr(self, '_current_user', None)  # this is to update the users
        self.kanban_report.save()
        return result

    def get_base_model(self):
        return self.report_type.content_type.model_class()

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('order',)


class CalendarReport(Report):
    VIEW_TYPE_CODES = {
        CALENDAR_VIEW_TYPE_MONTH: 'dayGridMonth',
        CALENDAR_VIEW_TYPE_GRID_WEEK: 'timeGridWeek',
        CALENDAR_VIEW_TYPE_LIST_WEEK: 'listWeek',
        CALENDAR_VIEW_TYPE_DAY: 'timeGridDay',
        CALENDAR_VIEW_TYPE_YEAR: 'year',
    }

    height = models.PositiveSmallIntegerField(default=600)
    view_type = models.PositiveSmallIntegerField(
        choices=CALENDAR_VIEW_TYPE_CHOICES,
        default=CALENDAR_VIEW_TYPE_MONTH,
    )

    def get_view_type_for_calendar(self, view_type=None):
        if view_type is None:
            view_type = self.view_type
        return self.VIEW_TYPE_CODES.get(view_type)


class CalendarReportDescription(TimeStampedModel):
    calendar_report = models.ForeignKey(CalendarReport, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    report_type = models.ForeignKey(ReportType, null=True, blank=False, on_delete=models.PROTECT)
    description = models.TextField(blank=True, null=True)
    order = models.PositiveSmallIntegerField()

    def save(self, *args, **kwargs):
        self.set_order_field(extra_filters={'calendar_report': self.calendar_report})
        return super().save(*args, **kwargs)

    def get_base_model(self):
        return self.report_type.content_type.model_class()

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('order',)


class CalendarReportDataSet(TimeStampedModel):
    DISPLAY_TYPE_NAME_AND_DESCRIPTION = 1
    DISPLAY_TYPE_DESCRIPTION_ONLY = 2
    DISPLAY_TYPE_HEADING_ONLY = 3

    DISPLAY_TYPE_CHOICES = (
        (DISPLAY_TYPE_NAME_AND_DESCRIPTION, 'Name and Description'),
        (DISPLAY_TYPE_DESCRIPTION_ONLY, 'Description Only'),
        (DISPLAY_TYPE_HEADING_ONLY, 'Heading Only'),
    )

    END_DATE_TYPE_FIELD = 1
    END_DATE_TYPE_DURATION_FIELD = 2
    END_DATE_TYPE_DURATION_FIXED = 3

    END_DATE_TYPE_CHOICES = (
        (END_DATE_TYPE_FIELD, 'Field'),
        (END_DATE_TYPE_DURATION_FIELD, 'Duration Field'),
        (END_DATE_TYPE_DURATION_FIXED, 'Duration Fixed'),
    )

    calendar_report = models.ForeignKey(CalendarReport, on_delete=models.CASCADE)
    order = models.PositiveSmallIntegerField()
    report_type = models.ForeignKey(ReportType, null=True, blank=False, on_delete=models.PROTECT)
    heading_field = models.CharField(max_length=200, blank=True, null=True)
    name = models.CharField(max_length=200)
    display_type = models.PositiveSmallIntegerField(
        choices=DISPLAY_TYPE_CHOICES,
        default=DISPLAY_TYPE_NAME_AND_DESCRIPTION,
    )
    start_date_field = models.CharField(max_length=200, blank=True, null=True)
    end_date_type = models.PositiveSmallIntegerField(
        choices=END_DATE_TYPE_CHOICES,
        default=END_DATE_TYPE_FIELD,
    )
    end_date_field = models.CharField(max_length=200, blank=True, null=True)
    end_duration_field = models.CharField(max_length=200, blank=True, null=True)
    end_duration = models.PositiveSmallIntegerField(blank=True, null=True)
    background_colour_field = models.CharField(max_length=200, blank=True, null=True)
    link_field = models.CharField(max_length=200, blank=True, null=True)
    calendar_report_description = models.ForeignKey(
        CalendarReportDescription, null=True, blank=False, on_delete=models.CASCADE
    )
    query_data = models.JSONField(null=True, blank=True)

    def save(self, *args, **kwargs):
        self.set_order_field(extra_filters={'calendar_report': self.calendar_report})
        return super().save(*args, **kwargs)

    def get_base_model(self):
        return self.report_type.content_type.model_class()

    class Meta:
        ordering = ('order',)


class KanbanReportLane(TimeStampedModel):
    MULTIPLE_TYPE_NA = 0
    MULTIPLE_TYPE_DAILY = 1
    MULTIPLE_TYPE_DAILY_WITHIN = 2
    MULTIPLE_TYPE_WEEKLY = 3
    MULTIPLE_TYPE_WEEKLY_WITHIN = 4
    MULTIPLE_TYPE_MONTHLY = 5
    MULTIPLE_TYPE_MONTHLY_WITHIN = 6

    MULTIPLE_TYPE_CHOICES = [
        (MULTIPLE_TYPE_NA, 'N/A'),
        (MULTIPLE_TYPE_DAILY, 'Daily (single date)'),
        (MULTIPLE_TYPE_DAILY_WITHIN, 'Daily (within two date)'),
        (MULTIPLE_TYPE_WEEKLY, 'Weekly (single date)'),
        (MULTIPLE_TYPE_WEEKLY_WITHIN, 'Weekly (within two date)'),
        (MULTIPLE_TYPE_MONTHLY, 'Monthly (single date)'),
        (MULTIPLE_TYPE_MONTHLY_WITHIN, 'Monthly (within two date)'),
    ]

    kanban_report = models.ForeignKey(KanbanReport, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    order = models.PositiveSmallIntegerField()
    report_type = models.ForeignKey(ReportType, null=True, blank=False, on_delete=models.PROTECT)
    heading_field = models.CharField(max_length=200, blank=True, null=True)
    link_field = models.CharField(max_length=200, blank=True, null=True)
    order_by_field = models.CharField(max_length=200, blank=True, null=True)
    order_by_ascending = models.BooleanField(default=True)
    kanban_report_description = models.ForeignKey(
        KanbanReportDescription, null=True, blank=False, on_delete=models.CASCADE
    )

    multiple_type = models.PositiveIntegerField(choices=MULTIPLE_TYPE_CHOICES, default=MULTIPLE_TYPE_NA)
    multiple_type_label = models.CharField(max_length=200, blank=True, null=True)
    multiple_type_date_field = models.CharField(max_length=200, blank=True, null=True)
    multiple_type_end_date_field = models.CharField(max_length=200, blank=True, null=True)

    # this could be choice field from RANGE_TYPE_CHOICES however if one adds a new one it creates a new migration!
    multiple_start_period = models.PositiveSmallIntegerField(blank=True, null=True)
    multiple_end_period = models.PositiveSmallIntegerField(blank=True, null=True)
    background_colour_field = models.CharField(max_length=200, blank=True, null=True)
    heading_colour_field = models.CharField(max_length=200, blank=True, null=True)

    query_data = models.JSONField(null=True, blank=True)

    def save(self, *args, **kwargs):
        self.set_order_field(extra_filters={'kanban_report': self.kanban_report})
        result = super().save(*args, **kwargs)
        self.kanban_report._current_user = getattr(self, '_current_user', None)  # this is to update the users
        self.kanban_report.save()
        return result

    def get_base_model(self):
        return self.report_type.content_type.model_class()

    class Meta:
        ordering = ('order',)


class CustomReport(Report):
    output_type = models.CharField(max_length=200, blank=True, null=True)
    view_name = models.CharField(max_length=200)
    settings = models.JSONField(null=True, blank=True)


class Dashboard(TimeStampedModel):
    slug = models.SlugField(unique=True)
    slug_alias = models.SlugField(blank=True, null=True)  # used if the slug changes
    name = models.CharField(max_length=200)
    display_option = models.PositiveIntegerField(choices=DISPLAY_OPTION_CHOICES[1:], default=DISPLAY_OPTION_2_PER_ROW)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        slug_alias = self.slug
        self.make_new_slug(allow_dashes=False, on_edit=True)
        if slug_alias != self.slug:
            self.slug_alias = slug_alias
        return super().save(*args, **kwargs)


class DashboardReport(TimeStampedModel):
    dashboard = models.ForeignKey(Dashboard, on_delete=models.CASCADE)
    order = models.PositiveSmallIntegerField()
    report = models.ForeignKey(Report, on_delete=models.CASCADE)
    top = models.BooleanField(default=False)
    name_override = models.CharField(max_length=200, blank=True, null=True)
    display_option = models.PositiveIntegerField(choices=DISPLAY_OPTION_CHOICES, default=DISPLAY_OPTION_NONE)
    show_versions = models.BooleanField(default=True)
    report_query = models.ForeignKey(ReportQuery, blank=True, null=True, on_delete=models.CASCADE)
    options = models.JSONField(null=True, blank=True)

    def get_class(self, extra_class_name):
        if self.display_option != DISPLAY_OPTION_NONE:
            class_names = DISPLAY_OPTION_CLASSES.get(self.display_option)
        else:
            class_names = DISPLAY_OPTION_CLASSES.get(self.dashboard.display_option)

        if extra_class_name:
            class_names += f' {extra_class_name}'

        return class_names

    def save(self, *args, **kwargs):
        self.set_order_field(extra_filters={'dashboard': self.dashboard, 'top': self.top})
        return super().save(*args, **kwargs)

    class Meta:
        ordering = ['order']
