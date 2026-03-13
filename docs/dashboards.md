# Dashboards

Dashboards combine multiple reports into a single page with a configurable layout.

## Dashboard model

A dashboard is a container that holds one or more `DashboardReport` entries, each linking to a report with layout options.

## Creating a dashboard

Dashboards are created and edited through the modal-based UI. You can:

- Set a **name** and **slug** for the dashboard
- Choose a **display option** to control the number of reports per row
- Add reports from the existing report library
- Reorder reports using the **order** field

## Layout options

The `display_option` field controls how reports are arranged:

| Option | Description |
|---|---|
| None / Default | Inherits from individual report settings |
| 1 per row | Full-width reports |
| 2 per row | Two reports side by side |
| 3 per row | Three reports per row |
| 4 per row | Four reports per row |
| 6 per row | Six reports per row |

Each dashboard report can also override the dashboard-level display option with its own `display_option` setting.

## Dashboard report options

Each report within a dashboard supports:

| Option | Description |
|---|---|
| `name_override` | Override the report's name for this dashboard |
| `order` | Position within the dashboard |
| `display_option` | Layout override for this report |
| `size` | Standard or Large |
| `show_versions` | Show version selector for the report |
| `report_query` | Use a specific query version |
| `show_options` | Show options selector |
| `options` | Pre-selected option |

## Settings

Configure the URL names for your report and dashboard views in Django settings:

```python
REPORT_BUILDER_DETAIL_URL_NAME = 'myapp:view_report'
REPORT_BUILDER_DASHBOARD_URL_NAME = 'myapp:view_dashboard'
```
