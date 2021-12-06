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
    extra_query = models.JSONField(null=True, blank=True)  # used for single value percent_divider_query_data

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
    SINGLE_VALUE_TYPE_AVERAGE = 5

    SINGLE_VALUE_TYPE_CHOICES = (
        (SINGLE_VALUE_TYPE_COUNT, 'Count'),
        (SINGLE_VALUE_TYPE_SUM, 'Sum'),
        (SINGLE_VALUE_TYPE_COUNT_AND_SUM, 'Count & Sum'),
        (SINGLE_VALUE_TYPE_PERCENT, 'Percent'),
        (SINGLE_VALUE_TYPE_AVERAGE, 'Average')
    )

    tile_colour = models.CharField(max_length=10, blank=True, null=True)
    field = models.CharField(max_length=200, blank=True, null=True)
    single_value_type = models.PositiveSmallIntegerField(choices=SINGLE_VALUE_TYPE_CHOICES,
                                                         default=SINGLE_VALUE_TYPE_COUNT, null=True, blank=True)
    decimal_places = models.IntegerField(default=0)


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

    class Meta:
        ordering = ['order']

