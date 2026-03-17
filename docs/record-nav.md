# Record navigation

Record navigation adds a prev/next bar at the top of detail pages when navigating from a report. This lets users step through records without returning to the report each time.

## How it works

1. A user clicks a row or link in a report datatable
2. The URLs of all visible rows are saved to `sessionStorage` (tab-scoped)
3. On the target page a navigation bar appears with previous/next buttons, a position indicator, a link back to the report, and a close button
4. Left/right arrow keys navigate between records (when not focused on a form field)
5. Navigating back to the report page automatically clears the nav bar
6. Clicking the X button dismisses it manually

Because `sessionStorage` is tab-scoped, two browser tabs with different filters each get their own independent navigation context.

## Enabling record navigation

Record navigation is controlled per report via a **Record Nav** toggle in the report edit modal.

### Table reports

The toggle appears in the table report modal alongside page length and other options.

### Breakdown reports

For single value, bar chart and multi-value reports the toggle appears when **Show Breakdown** is enabled. When a user opens the breakdown modal and clicks a link, the record navigation bar will appear on the linked page.

## Placeholder

The navigation bar is injected into a placeholder element:

```html
<div id="record-nav-placeholder"></div>
```

Add this to your base template between the header and main content. If the placeholder is not present the bar is inserted before the first `<main role="main">` element instead.

## Including the JavaScript

The `record_nav` package must be loaded on every page so the navigation bar can render on detail pages:

```django
{% lib_include 'record_nav' module='advanced_report_builder.includes' %}
```

Alternatively, add `RecordNavInclude` to your project's standard includes package.

## Using with custom datatables

The record navigation plugin can be added to any django-datatables table, not just report builder reports:

```python
from advanced_report_builder.record_nav import RecordNavPlugin

def setup_table(self, table):
    # ... configure table ...
    table.add_plugin(RecordNavPlugin, 'My Report Title')
```

The plugin handles two modes automatically:

- **row_href mode** -- when the table uses `table.table_options['row_href']`, URLs are computed from all visible rows
- **Link column mode** -- when the table uses `ReportBuilderColumnLink` or `ColumnLink` columns, URLs are collected from `<a>` tags in the clicked column

## Settings

### REPORT_BUILDER_RECORD_NAV_DEFAULT

Controls the default value of the **Record Nav** toggle when creating new reports.

```python
# Default: True (record nav enabled for new reports)
REPORT_BUILDER_RECORD_NAV_DEFAULT = False
```

Existing reports are not affected by this setting -- they keep their saved value.
