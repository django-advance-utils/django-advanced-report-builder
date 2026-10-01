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

### ADVANCED_REPORT_BUILDER_RESTRICT_QUERYSET

A callable, or the dotted path of one, taking `(queryset, request)` and returning the rows that request's user may see. Use it when some users must not see some rows at all (one brand of a group, a sales team's own customers). The report builder calls it on every queryset it reads report rows from, so tables, charts, single values, multi-value cells, kanban and calendar lanes, custom reports, breakdowns, report options and the query builder's filter-by-value lists all leave those rows out. Report rows can no longer be edited through the table's row-edit request. Not set, nothing changes.

Add `ReportBuilderRequestMiddleware` too, so querysets built away from a view (a column's option list) still know whose they are. If the hook is set and no request can be found (the middleware is missing, or a report is built in a background task), the hook is called with `None` and a warning is logged: **return no rows then**, so a missing request can never show everything.

```python
ADVANCED_REPORT_BUILDER_RESTRICT_QUERYSET = 'myapp.reports.restrict'

MIDDLEWARE = [
    # ...
    'advanced_report_builder.restrict.ReportBuilderRequestMiddleware',
]


# myapp/reports.py
def restrict(queryset, request):
    if queryset.model is not Order:
        return queryset
    if request is None:
        return queryset.none()  # fail closed
    if request.user.is_superuser:
        return queryset
    return queryset.filter(team_id__in=request.user.team_ids())
```

Write the filter on the model's own fields or a single-valued relation, or as `pk__in=<subquery>`. The hook runs after the report has added its totals and annotations, so a filter across a many-valued relation would add a join and inflate sums and counts.

It narrows the report's own rows. A column that aggregates a *related* model's rows (a reverse foreign key column, or a sum across a relation) counts every related row of each visible row; if the restriction is on that related model, restrict it there as well.

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
