# Installation

## Requirements

- Python >= 3.6
- Django >= 3.2
- PostgreSQL (required for array aggregation and advanced query features)

## Install the package

```bash
pip install django-advanced-report-builder
```

## Dependencies

The following packages are installed automatically:

| Package | Purpose |
|---|---|
| `django-filtered-datatables` | Table rendering and filtering |
| `django-ajax-helpers` | AJAX request handling |
| `django-nested-modals` | Modal dialog framework |
| `time-stamped-model` | Automatic created/updated timestamps |
| `date-offset` | Date arithmetic utilities |
| `expression-builder` | Query expression building |

## Add to INSTALLED_APPS

Add `advanced_report_builder` and its dependencies to your `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ...
    'ajax_helpers',
    'crispy_forms',
    'django_menus',
    'django_modals',
    'django_datatables',
    'advanced_report_builder',
    # ...
]
```

## Configure URLs

Include the report builder URLs in your root URL configuration:

```python
from django.urls import include, path

urlpatterns = [
    # ...
    path(
        'advanced-report-builder/',
        include('advanced_report_builder.urls', namespace='advanced_report_builder'),
    ),
    # ...
]
```

## Run migrations

```bash
python manage.py migrate
```

## Crispy Forms

The report builder uses `crispy_forms` for form rendering. Set the template pack in your settings:

```python
CRISPY_TEMPLATE_PACK = 'bootstrap4'
```
