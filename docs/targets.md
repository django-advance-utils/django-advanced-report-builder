# Targets

Targets allow you to define KPIs and goals that can be tracked against report data, particularly in line charts.

## Target model

A target represents a measurable goal with:

| Field | Description |
|---|---|
| `name` | Display name |
| `slug` | URL-safe identifier |
| `target_type` | The type of target |
| `period_type` | How often the target is measured (daily, weekly, monthly, quarterly, yearly) |
| `default_value` | The default target value |
| `default_percentage` | The default target as a percentage |
| `override_data` | JSON field for period-specific overrides |

## Period types

| Period | Description |
|---|---|
| No period | A static target with no time component |
| Daily | Target measured per day |
| Weekly | Target measured per week |
| Monthly | Target measured per month |
| Quarterly | Target measured per quarter |
| Yearly | Target measured per year |

## Target colours

Each target can have colour thresholds that change the display colour based on performance:

| Field | Description |
|---|---|
| `percentage` | The threshold percentage |
| `colour` | The hex colour to display when at or above this threshold |

This allows traffic-light style indicators (e.g. red below 50%, amber at 75%, green at 100%).

## Using targets with line charts

Line chart reports can have targets attached. When targets are enabled on a line chart:

- Target lines are drawn on the chart
- Performance against the target is visually indicated
- Colour thresholds provide at-a-glance status
