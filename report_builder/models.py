import json

from django.contrib.contenttypes.models import ContentType
from django.db import models
from time_stamped_model.models import TimeStampedModel


class ReportType(TimeStampedModel):
    name = models.CharField(max_length=200)
    content_type = models.ForeignKey(ContentType, null=False, blank=False, on_delete=models.PROTECT)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Report(TimeStampedModel):
    name = models.CharField(max_length=200)
    report_type = models.ForeignKey(ReportType, null=True, blank=False, on_delete=models.PROTECT)
    instance_type = models.CharField(null=True, max_length=255)
    search_filter_data = models.TextField(null=True, blank=True)  # To store the current query.

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

    def get_report(self):
        return getattr(self, self.instance_type)

    def get_title(self):
        return self.name

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if self.instance_type is None:
            self.instance_type = self._meta.label_lower.split('.')[1]
        return super().save(force_insert=force_insert, force_update=force_update,
                            using=using, update_fields=update_fields)


class TableReport(Report):
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

