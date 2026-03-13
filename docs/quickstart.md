# Quick start

This guide walks through adding the report builder to an existing Django project with a simple model.

## 1. Define a model with ReportBuilder

Add a `ReportBuilder` inner class to any model you want to report on:

```python
from django.db import models
from time_stamped_model.models import TimeStampedModel
from advanced_report_builder.report_builder import ReportBuilderFields


class Company(TimeStampedModel):
    name = models.CharField(max_length=80)
    active = models.BooleanField(default=False)
    importance = models.IntegerField(null=True)

    class ReportBuilder(ReportBuilderFields):
        colour = '#00008b'
        title = 'Company'
        fields = ['name', 'active', 'importance']
        default_columns = ['.id']

    def __str__(self):
        return self.name
```

## 2. Create a report type

The report builder needs at least one `ReportType` record in the database that points to the model's content type. Report types are created through the Django admin or programmatically:

```python
from django.contrib.contenttypes.models import ContentType
from advanced_report_builder.models import ReportType

content_type = ContentType.objects.get_for_model(Company)
ReportType.objects.create(
    content_type=content_type,
    report_builder_class_name='myapp.Company.ReportBuilder',
)
```

## 3. Create views for reports and dashboards

You need to provide views in your application that render individual reports and dashboards. Set the URL names in your settings:

```python
REPORT_BUILDER_DETAIL_URL_NAME = 'myapp:view_report'
REPORT_BUILDER_DASHBOARD_URL_NAME = 'myapp:view_dashboard'
```

## 4. Use the UI

Once configured, the report builder provides a full modal-based interface for:

- Creating and editing reports
- Selecting fields, filters, ordering and grouping
- Previewing results in real time
- Configuring charts, single values, kanban boards, calendars and more
- Building dashboards that combine multiple reports

## Example project

A complete working example is included in the repository under `django_examples/`. It uses Docker Compose for the PostgreSQL database:

```bash
cd django_examples
docker-compose up -d
python manage.py migrate
python manage.py import_report_builder
python manage.py runserver
```
