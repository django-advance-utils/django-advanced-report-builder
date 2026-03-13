[![PyPI version](https://badge.fury.io/py/django-advanced-report-builder.svg)](https://badge.fury.io/py/django-advanced-report-builder)


# Django advanced report builder

A Django application that provides a fully featured, dynamic report-building interface. It allows users to create, customise, preview and export reports directly through a dedicated front-end UI, without writing queries or touching the Django admin.

## Features

- Build reports through a standalone report-builder interface (not the Django admin).
- Choose a root model and dynamically select fields to display.
- Add filters, conditions, ordering and grouping.
- Preview results instantly within the UI.
- Export to CSV, Excel and other supported formats.
- Pluggable architecture for adding formats, custom filters, or integration hooks.
- Designed to integrate easily into existing Django projects.

## Documentation

Full documentation is available in the [docs](docs/index.md) directory:

- [Installation](docs/installation.md)
- [Quick start](docs/quickstart.md)
- [Model configuration](docs/model-configuration.md)
- [Report types](docs/report-types.md)
- [Dashboards](docs/dashboards.md)
- [Filters and queries](docs/filters-and-queries.md)
- [Custom columns](docs/custom-columns.md)
- [Targets](docs/targets.md)
- [Settings](docs/settings.md)
