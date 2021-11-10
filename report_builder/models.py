import json

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django_datatables.columns import DateColumn
from django_datatables.datatables import ColumnInitialisor
from time_stamped_model.models import TimeStampedModel

from report_builder.columns import ReportBuilderDateColumn
from report_builder.globals import ANNOTATION_VALUE_FUNCTIONS, ANNOTATION_FUNCTIONS, DATE_FIELDS, \
    DATE_FORMAT_TYPES_DJANGO_FORMAT
from report_builder.utils import split_attr


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

    def get_base_modal(self):
        return self.report_type.content_type.model_class()


class TableReport(Report):
    table_fields = models.TextField(null=True, blank=True)
    has_clickable_rows = models.BooleanField(default=False)  # This is for standard tables.
    pivot_fields = models.TextField(null=True, blank=True)

    def has_pivot_data(self):
        return self.pivot_fields is not None and self.pivot_fields != ''

    def get_pivot_fields(self):
        pivot_data = json.loads(self.pivot_fields)
        return pivot_data

    @staticmethod
    def get_date_field(table_field):
        data_attr = split_attr(table_field)
        field_name = table_field['field']
        date_format = data_attr.get('date_format')
        if date_format:
            date_format = DATE_FORMAT_TYPES_DJANGO_FORMAT[int(date_format)]

        date_function_kwargs = {'title': table_field.get('title'),
                                'date_format': date_format}

        if 'annotations_value' in data_attr:
            annotations_value = data_attr['annotations_value']
            new_field_name = f'{annotations_value}_{field_name}'
            function = ANNOTATION_VALUE_FUNCTIONS[annotations_value]
            date_function_kwargs['annotations_value'] = {new_field_name: function(field_name)}

            field_name = new_field_name

        date_function_kwargs.update({'field': field_name,
                                     'column_name': field_name})
        field = ReportBuilderDateColumn(**date_function_kwargs)
        return field

    def get_field_strings(self):
        table_fields = json.loads(self.table_fields)

        fields = []

        base_modal = self.get_base_modal()
        for table_field in table_fields:
            field = table_field['field']

            column_initialisor = ColumnInitialisor(start_model=base_modal, path=field)
            column_initialisor.get_columns()
            django_field = column_initialisor.django_field

            if isinstance(django_field, DATE_FIELDS):
                field = self.get_date_field(table_field=table_field)
            else:
                data_attr = split_attr(table_field)
                _attr = {}
                if 'title' in table_field:
                    _attr['title'] = table_field['title']

                if data_attr and 'annotations_type' in data_attr:
                    annotations_type = data_attr['annotations_type']
                    new_field_name = f'{annotations_type}_{field}'
                    function = ANNOTATION_FUNCTIONS[annotations_type]
                    _attr['annotations'] = {new_field_name: function(field)}
                    field = new_field_name

                if _attr:
                    field = (field, _attr)

            fields.append(field)
        return fields

