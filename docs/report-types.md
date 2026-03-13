# Report types

The report builder supports ten report types out of the box. Each type has its own modal-based editor and rendering view.

## Table report

Displays data in a paginated, sortable table powered by DataTables. Supports:

- Column selection and ordering
- Pivot columns (dynamic columns based on field values)
- Configurable page length
- CSV and Excel export
- Column alignment and formatting

## Single value report

Displays a single aggregated metric as a tile or gauge.

### Aggregation types

| Type | Description |
|---|---|
| Sum | Total of all values |
| Count | Number of records |
| Average | Mean value |
| Maximum | Highest value |
| Minimum | Lowest value |

### Display options

- **Tile colour** and **font colour** for styling
- **Decimal places** for numeric precision
- **Prefix** and **suffix** text
- **Percentage mode** using a numerator query
- **Breakdown** modal to show the underlying data
- **Gauge** template style as an alternative to the default tile

## Bar chart report

Renders data as a bar chart using Chart.js.

### Options

- **Orientation** -- vertical or horizontal
- **Stacking** -- stack bars or display side by side
- **Axis scale** -- time-based grouping by year, quarter, month, week or day
- **Date field** -- the field used for time-based grouping
- **Breakdown** modal to show the underlying data

## Line chart report

Renders data as a line chart, typically used for time-series data.

### Options

- **Axis scale** -- time-based grouping by year, quarter, month, week or day
- **Date field** -- the field used for time-based grouping
- **Targets** -- optional target lines for KPI tracking

## Pie chart report

Renders data as a pie or doughnut chart.

### Styles

- Pie
- Doughnut

## Funnel chart report

Renders data as a funnel visualisation, useful for conversion pipelines.

## Multi-value report

A grid-based layout where each cell is independently configured. Useful for dashboards, scorecards and summary panels.

### Features

- Configurable rows and columns
- Individual cell formulas and aggregations
- Cell styling (alignment, bold, italic, font size, font colour, background colour)
- Shared queries across cells (held queries)
- Column width configuration
- Copy cells to duplicate configuration

## Kanban report

Displays data as a kanban board with configurable lanes.

### Configuration

- **Lanes** -- define columns on the board, each with its own query
- **Descriptions** -- event type definitions for card content
- Lanes can be duplicated for quick setup

## Calendar report

Displays data on a calendar powered by FullCalendar.

### View types

- Month
- Grid week
- List week
- Day
- Year

### Configuration

- **Data sets** -- each data set maps a query to calendar events with start date, end date or duration
- **Descriptions** -- event type definitions for display formatting
- **Height** -- calendar height in pixels

## Custom report

A report type backed by a custom Django view. Use this when none of the built-in report types fit your needs.

### Configuration

- **View name** -- the Django URL name for your custom view
- **Output type** -- the type of output your view produces
- **Settings** -- a JSON field for arbitrary configuration
