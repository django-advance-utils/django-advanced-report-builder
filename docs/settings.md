# Settings

All settings are optional and have sensible defaults.

## Report builder settings

### REPORT_BUILDER_DETAIL_URL_NAME

The Django URL name for the view that renders an individual report.

```python
REPORT_BUILDER_DETAIL_URL_NAME = 'myapp:view_report'
```

### REPORT_BUILDER_DASHBOARD_URL_NAME

The Django URL name for the view that renders a dashboard.

```python
REPORT_BUILDER_DASHBOARD_URL_NAME = 'myapp:view_dashboard'
```

### REPORT_BUILDER_CUSTOMISATION

Dotted path to a customisation class. Override this to provide custom initialisation hooks.

```python
# Default
REPORT_BUILDER_CUSTOMISATION = 'report_builder.customise.CustomiseReportBuilder'
```

### REPORT_BUILDER_VIEW_TYPES_CLASS

Dotted path to the class that defines available view types. Override this to add or remove report types.

```python
# Default
REPORT_BUILDER_VIEW_TYPES_CLASS = 'advanced_report_builder.view_types.ViewTypes'
```

The default `ViewTypes` class maps report types to their views:

```python
class ViewTypes:
    views = {
        'tablereport': TableView,
        'singlevaluereport': SingleValueView,
        'barchartreport': BarChartView,
        'linechartreport': LineChartView,
        'piechartreport': PieChartView,
        'funnelchartreport': FunnelChartView,
        'kanbanreport': KanbanView,
        'calendarreport': CalendarView,
        'multivaluereport': MultiValueView,
        'error': ErrorPodView,
    }
    custom_views = {}
```

### REPORT_BUILDER_TEMPLATE_TYPES_CLASS

Dotted path to the class that defines available template types. Override this to customise templates for report rendering.

```python
# Default
REPORT_BUILDER_TEMPLATE_TYPES_CLASS = 'advanced_report_builder.template_types.TemplateTypes'
```

### REPORT_BUILDER_RECORD_NAV_DEFAULT

Controls the default value of the **Record Nav** toggle when creating new reports. See [Record navigation](record-nav.md) for details.

```python
# Default: True (record nav enabled for new reports)
REPORT_BUILDER_RECORD_NAV_DEFAULT = False
```

### ADVANCED_REPORT_BUILDER_FIELD_EXTENSIONS

A dict mapping short keys to dotted paths of `FieldExtension` subclasses. Registered extensions can inject extra fields into the column edit modal on an opt-in per-render basis. See [Field extensions](field-extensions.md) for the full interface.

```python
ADVANCED_REPORT_BUILDER_FIELD_EXTENSIONS = {
    'my_extension': 'myapp.arb_extensions.MyExtension',
}
```

Registering an extension alone has no effect on existing modals; the owning modal must opt in by appending `extensions-<key>` to its `select_column_url` slug.

## Other settings

### FINANCIAL_YEAR_START_MONTH

The month number (1--12) when the financial year starts. Used by variable date range filters for financial year and quarter calculations.

```python
# Default: calendar year (January)
FINANCIAL_YEAR_START_MONTH = 3  # Financial year starts in March
```

### CRISPY_TEMPLATE_PACK

Required by `crispy_forms` for form rendering.

```python
CRISPY_TEMPLATE_PACK = 'bootstrap4'
```
