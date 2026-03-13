# Django Advanced Report Builder

A Django application that provides a fully featured, dynamic report-building interface. It allows users to create, customise, preview and export reports directly through a dedicated front-end UI, without writing queries or touching the Django admin.

## Features

- Build reports through a standalone report-builder interface (not the Django admin)
- Choose a root model and dynamically select fields to display
- Add filters, conditions, ordering and grouping
- Preview results instantly within the UI
- Export to CSV, Excel and other supported formats
- Pluggable architecture for adding formats, custom filters, or integration hooks
- Designed to integrate easily into existing Django projects

## Report types

- **Table** -- tabular data with sorting, pagination, pivot columns and CSV/Excel export
- **Single value** -- a single aggregated metric (sum, count, average, min, max) displayed as a tile or gauge
- **Bar chart** -- vertical or horizontal bar charts with optional stacking
- **Line chart** -- time-series line charts with optional targets
- **Pie chart** -- pie or doughnut charts
- **Funnel chart** -- funnel visualisation
- **Multi-value** -- grid-based layouts with individually configured cells, formulas and styling
- **Kanban** -- kanban board layout with configurable lanes
- **Calendar** -- calendar event display powered by FullCalendar
- **Custom** -- user-defined reports backed by a custom view

## Contents

- [Installation](installation.md)
- [Quick start](quickstart.md)
- [Model configuration](model-configuration.md)
- [Report types](report-types.md)
- [Dashboards](dashboards.md)
- [Filters and queries](filters-and-queries.md)
- [Custom columns](custom-columns.md)
- [Targets](targets.md)
- [Settings](settings.md)
