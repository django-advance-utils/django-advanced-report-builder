# Filters and queries

The report builder includes a powerful query builder for filtering and ordering report data.

## Query builder

Each report can have one or more `ReportQuery` entries. Queries are built through the modal-based UI and stored as JSON.

### Filter operators

The available filter operators depend on the field type:

**String fields:**
- Equals / not equals
- Contains / not contains
- Starts with / not starts with
- Ends with / not ends with
- Is empty / is not empty

**Number fields:**
- Equals / not equals
- Greater than / greater than or equal to
- Less than / less than or equal to
- Between
- Is empty / is not empty

**Date fields:**
- Equals / not equals
- Greater than / greater than or equal to
- Less than / less than or equal to
- Between
- Is empty / is not empty
- Variable date ranges (see below)

**Boolean fields:**
- Equals

**Choice fields:**
- In / not in

## Variable date ranges

The report builder supports over 65 variable date ranges for date filters, allowing reports to stay current without manual updates.

### Examples

| Range | Description |
|---|---|
| Today | Current date |
| Yesterday | Previous date |
| This week | Current week (Mon--Sun) |
| Last week | Previous week |
| This month | Current calendar month |
| Last month | Previous calendar month |
| Last 7 days | Rolling 7-day window |
| Last 30 days | Rolling 30-day window |
| Last 12 months | Rolling 12-month window |
| This year | Current calendar year |
| Last year | Previous calendar year |
| This financial year | Current financial year |
| Last financial year | Previous financial year |
| This financial quarter | Current financial quarter |
| Last financial quarter | Previous financial quarter |

The financial year start month is configurable via the `FINANCIAL_YEAR_START_MONTH` setting (defaults to the calendar year).

## Ordering

Each query can have one or more `ReportQueryOrder` entries that define the sort order:

- **Field** -- the field to sort by
- **Ascending** -- sort direction
- **Order** -- priority when multiple sort fields are used

## Multiple queries

Reports support multiple named queries (versions). This allows you to:

- Save different filter configurations for the same report
- Switch between query versions in the UI
- Use specific query versions when embedding reports in dashboards

## Extra queries

Reports can also have an `extra_query` field for additional filtering that is applied on top of the main query. This is useful for applying global filters or security constraints.
