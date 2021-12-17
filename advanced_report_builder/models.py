import json

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django_datatables.columns import DatatableColumn, NoHeadingColumn
from django_datatables.model_def import DatatableModel
from time_stamped_model.models import TimeStampedModel

from advanced_report_builder.globals import DISPLAY_OPTION_CHOICES, DISPLAY_OPTION_2_PER_ROW, DISPLAY_OPTION_NONE, \
    DISPLAY_OPTION_CLASSES


class ReportType(TimeStampedModel):
    name = models.CharField(max_length=200)
    content_type = models.ForeignKey(ContentType, null=False, blank=False, on_delete=models.PROTECT)
    report_builder_class_name = models.CharField(max_length=200)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Report(TimeStampedModel):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    slug_alias = models.SlugField(blank=True, null=True)  # used if the slug changes
    report_type = models.ForeignKey(ReportType, null=True, blank=False, on_delete=models.PROTECT)
    instance_type = models.CharField(null=True, max_length=255)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

    def get_report(self):
        return getattr(self, self.instance_type)

    def get_title(self):
        return self.name

    def save(self, *args, **kwargs):

        slug_alias = self.slug
        self.make_new_slug(allow_dashes=False, on_edit=True)
        if slug_alias != self.slug:
            self.slug_alias = slug_alias

        if self.instance_type is None:
            self.instance_type = self._meta.label_lower.split('.')[1]
        return super().save(*args, **kwargs)

    def get_base_modal(self):
        return self.report_type.content_type.model_class()

    class Datatable(DatatableModel):

        class OutputType(DatatableColumn):
            output_types = {'tablereport': 'Table',
                            'singlevaluereport': 'Single Value'}

            def col_setup(self):
                self.field = ['instance_type']

            # noinspection PyMethodMayBeStatic
            def row_result(self, data, _page_data):
                instance_type = data[self.model_path + 'instance_type']
                return self.output_types.get(instance_type, '')

        class OutputTypeIcon(NoHeadingColumn):
            output_types = {'tablereport': '<i class="fas fa-table"></i>',
                            'singlevaluereport': '<i class="fas fa-box-open"></i>'}

            def col_setup(self):
                self.field = ['instance_type']

            # noinspection PyMethodMayBeStatic
            def row_result(self, data, _page_data):
                instance_type = data[self.model_path + 'instance_type']
                return self.output_types.get(instance_type, '')


class ReportQuery(TimeStampedModel):
    report = models.ForeignKey(Report, on_delete=models.CASCADE)
    name = models.TextField(default='Standard')
    query = models.JSONField(null=True, blank=True)
    extra_query = models.JSONField(null=True, blank=True)  # used for single value Numerator

    class Meta:
        ordering = ['name']
        unique_together = ('name', 'report')
        verbose_name_plural = 'Report queries'


class TableReport(Report):
    table_fields = models.TextField(null=True, blank=True)
    has_clickable_rows = models.BooleanField(default=False)  # This is for standard tables.
    pivot_fields = models.TextField(null=True, blank=True)
    page_length = models.PositiveSmallIntegerField(choices=((10, '10'),
                                                            (25, '25'),
                                                            (50, '50'),
                                                            (100, '100'),
                                                            (150, '150'),
                                                            (200, '200')), default=100)

    def has_pivot_data(self):
        return self.pivot_fields is not None and self.pivot_fields != ''

    def get_pivot_fields(self):
        pivot_data = json.loads(self.pivot_fields)
        return pivot_data


class SingleValueReport(Report):
    SINGLE_VALUE_TYPE_COUNT = 1
    SINGLE_VALUE_TYPE_SUM = 2
    SINGLE_VALUE_TYPE_COUNT_AND_SUM = 3
    SINGLE_VALUE_TYPE_PERCENT = 4
    SINGLE_VALUE_TYPE_PERCENT_FROM_COUNT = 5
    SINGLE_VALUE_TYPE_AVERAGE = 6

    SINGLE_VALUE_TYPE_CHOICES = (
        (SINGLE_VALUE_TYPE_COUNT, 'Count'),
        (SINGLE_VALUE_TYPE_SUM, 'Sum'),
        (SINGLE_VALUE_TYPE_COUNT_AND_SUM, 'Count & Sum'),
        (SINGLE_VALUE_TYPE_PERCENT, 'Percent'),
        (SINGLE_VALUE_TYPE_PERCENT_FROM_COUNT, 'Percent from Count'),
        (SINGLE_VALUE_TYPE_AVERAGE, 'Average')
    )

    tile_colour = models.CharField(max_length=10, blank=True, null=True)
    field = models.CharField(max_length=200, blank=True, null=True)  # denominator
    numerator = models.CharField(max_length=200, blank=True, null=True)
    single_value_type = models.PositiveSmallIntegerField(choices=SINGLE_VALUE_TYPE_CHOICES,
                                                         default=SINGLE_VALUE_TYPE_COUNT)
    decimal_places = models.IntegerField(default=0)


class BarChartReport(Report):
    X_AXIS_SCALE_YEARLY = 0
    X_AXIS_SCALE_MONTHLY = 1
    X_AXIS_SCALE_WEEKLY = 2
    X_AXIS_SCALE_DAILY = 3

    X_AXIS_SCALE_OPTIONS = (
        (X_AXIS_SCALE_YEARLY, 'Yearly'),
        (X_AXIS_SCALE_MONTHLY, 'Monthly'),
        (X_AXIS_SCALE_WEEKLY, 'Weekly'),
        (X_AXIS_SCALE_DAILY, 'Daily')
    )

    AXIS_VALUE_TYPE_COUNT = 1
    AXIS_VALUE_TYPE_SUM = 2
    AXIS_VALUE_TYPE_AVERAGE = 3

    AXIS_VALUE_TYPE_CHOICES = (
        (AXIS_VALUE_TYPE_COUNT, 'Count'),
        (AXIS_VALUE_TYPE_SUM, 'Sum'),
        (AXIS_VALUE_TYPE_AVERAGE, 'Average')
    )

    BAR_CHART_ORIENTATION_VERTICAL = 'bar'
    BAR_CHART_ORIENTATION_HORIZONTAL = 'horizontalBar'

    BAR_CHART_ORIENTATION_CHOICES = (
        (BAR_CHART_ORIENTATION_VERTICAL, 'Vertical'),
        (BAR_CHART_ORIENTATION_HORIZONTAL, 'Horizontal')
    )

    axis_scale = models.PositiveSmallIntegerField(choices=X_AXIS_SCALE_OPTIONS, default=X_AXIS_SCALE_YEARLY,
                                                  null=True, blank=True)
    date_field = models.CharField(max_length=200, blank=True, null=True)
    axis_value_type = models.PositiveSmallIntegerField(choices=AXIS_VALUE_TYPE_CHOICES,
                                                       default=AXIS_VALUE_TYPE_COUNT, null=True, blank=True)
    fields = models.TextField(null=True, blank=True)
    x_label = models.CharField(max_length=200, blank=True, null=True)
    y_label = models.CharField(max_length=200, blank=True, null=True)

    bar_chart_orientation = models.CharField(choices=BAR_CHART_ORIENTATION_CHOICES,
                                             default=BAR_CHART_ORIENTATION_VERTICAL,
                                             max_length=200)
    show_totals = models.BooleanField(default=False)

    def is_orientation_vertical(self):
        return self.bar_chart_orientation == self.BAR_CHART_ORIENTATION_VERTICAL


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

    def get_class(self):
        if self.display_option != DISPLAY_OPTION_NONE:
            return DISPLAY_OPTION_CLASSES.get(self.display_option)
        return DISPLAY_OPTION_CLASSES.get(self.dashboard.display_option)

    def save(self, *args, **kwargs):
        self.set_order_field(extra_filters={'dashboard': self.dashboard,
                                            'top': self.top})
        return super().save(*args, **kwargs)

    class Meta:
        ordering = ['order']

