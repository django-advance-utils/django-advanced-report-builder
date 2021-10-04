import json

from django.contrib.contenttypes.models import ContentType
from django.db.models.base import ModelBase
from time_stamped_model.models import TimeStampedModel
from django.db import models

from report_builder import OUTPUT_TYPE_CALENDAR, OUTPUT_TYPE_TABLE, \
    OUTPUT_TYPE_BAR_CHART, OUTPUT_TYPE_SINGLE_VALUE, OUTPUT_TYPE_CUSTOM, OUTPUT_TYPE_LINE_CHART, OUTPUT_TYPE_FUNNEL


class ReportTypeBase(TimeStampedModel):
    name = models.CharField(max_length=200)
    content_type = models.ForeignKey(ContentType, null=False, blank=False, on_delete=models.PROTECT)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        abstract = True


class TableReportBase(models.Model):
    # This is the field that holds the selected fields, needs to be a dict.
    table_fields = models.TextField(null=True, blank=True)
    has_clickable_rows = models.BooleanField(default=False)  # This is for standard tables.
    pivot_fields = models.TextField(null=True, blank=True)

    def has_pivot_data(self):
        return self.pivot_fields is not None and self.pivot_fields != ''

    def get_pivot_fields(self):
        pivot_data = json.loads(self.pivot_fields)
        return pivot_data

    def get_field_strings(self):
        table_fields = json.loads(self.table_fields)

        fields = []
        for table_field in table_fields:
            if 'title' in table_field:
                fields.append((table_field['field'], table_field['title']))
            else:
                fields.append(table_field['field'])
        return fields

    class Meta:
        abstract = True


class ReportMeta(ModelBase):
    """
    This dynamically adds the other models needed to run reports
    """

    def __new__(cls, name, bases, attrs, **kwargs):
        module_name = attrs['__module__']

        sub_model = attrs.pop('sub_model', False)

        if not sub_model and name != "ReportBase":
            attr_report_type = {
                '__module__': module_name
            }
            report_type_cls = ModelBase(f"{name}ReportType", (ReportTypeBase,), attr_report_type)
            attrs['report_type'] = models.ForeignKey(report_type_cls, null=True, blank=False, on_delete=models.PROTECT)

        super_new_cls = super().__new__(cls, name, bases, attrs)
        if not sub_model and name != "ReportBase":
            attr_report_type = {
                'sub_model': True,
                '__module__': module_name
            }
            ReportMeta(f"{name}TableReport", (TableReportBase, super_new_cls,), attr_report_type)

        return super_new_cls


class ReportBase(TimeStampedModel, metaclass=ReportMeta):
    OUTPUT_TYPE_CHOICES = (
        (OUTPUT_TYPE_TABLE, 'Table'),
        (OUTPUT_TYPE_CALENDAR, 'Calendar'),
        (OUTPUT_TYPE_BAR_CHART, 'Bar Chart'),
        (OUTPUT_TYPE_SINGLE_VALUE, 'Single Value'),
        (OUTPUT_TYPE_CUSTOM, 'Custom'),
        (OUTPUT_TYPE_LINE_CHART, 'Line Chart'),
        (OUTPUT_TYPE_FUNNEL, 'Funnel'),
    )

    name = models.CharField(max_length=200)
    # report_type = gets added in ReportMeta
    output_type = models.PositiveSmallIntegerField(choices=OUTPUT_TYPE_CHOICES)
    search_filter_data = models.TextField(null=True, blank=True)  # To store the current query.

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        abstract = True

    def get_report(self):
        output_type = self.output_type

        model_name = self._meta.model_name

        if output_type == OUTPUT_TYPE_TABLE:
            return getattr(self, f"{model_name}tablereport")

        return None

    def get_model_name(self):
        return self._meta.model_name

    def get_title(self):
        return self.name

