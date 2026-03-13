# Model configuration

To make a Django model available to the report builder, add an inner class called `ReportBuilder` that inherits from `ReportBuilderFields`.

```python
from advanced_report_builder.report_builder import ReportBuilderFields

class MyModel(models.Model):
    # ... fields ...

    class ReportBuilder(ReportBuilderFields):
        colour = '#00008b'
        title = 'My Model'
        fields = ['field_a', 'field_b']
```

## ReportBuilderFields reference

| Attribute | Type | Default | Description |
|---|---|---|---|
| `colour` | `str` | `None` | Hex colour used to identify this model in the UI |
| `title` | `str` | `None` | Display name shown in the report builder |
| `fields` | `list` | `[]` | Field names (or column instances) available for reports |
| `default_columns` | `list` | `[]` | Columns shown by default when creating a new table report. Use `'.id'` to include the primary key |
| `includes` | `dict` | `{}` | Related models to make available (see [Includes](#includes)) |
| `pivot_fields` | `dict` | `{}` | Fields that can be used as pivot columns (see [Pivot fields](#pivot-fields)) |
| `field_classes` | `dict` | `{'record_count': RecordCountColumn()}` | Custom column class instances keyed by field name |
| `exclude_search_fields` | `set` | `set()` | Fields to exclude from search |
| `exclude_display_fields` | `set` | `set()` | Fields to exclude from display |
| `order_by_fields` | `set` | `set()` | Fields for default ordering |
| `url` | `str` | `None` | Custom URL for the model |
| `extra_chart_field` | `list` | `['record_count']` | Extra fields available in chart reports |
| `default_multiple_column_text` | `str` | `''` | Format string for multi-value display (e.g. `'{name} - {code}'`) |
| `default_multiple_column_fields` | `list` | `[]` | Fields used in `default_multiple_column_text` |
| `default_multiple_pk` | `str` | `'id'` | Primary key field for multi-value lookups |
| `options_filter` | `Q` | `Q()` | Django Q object to filter options |
| `option_label` | `str` | `'__str__'` | Method used for option labels |
| `option_ajax_search` | `list` | `[]` | Fields for AJAX search (e.g. `['name__icontains']`) |

## Using properties

Any attribute can be defined as a `@property` for dynamic configuration:

```python
class Company(models.Model):
    class ReportBuilder(ReportBuilderFields):
        colour = '#00008b'
        title = 'Company'

        @property
        def fields(self):
            return ['name', 'active', 'importance', 'custom_column']

        @property
        def includes(self):
            return {
                'user_profile': {
                    'title': 'User',
                    'model': 'myapp.UserProfile.ReportBuilder',
                }
            }
```

## Fields

The `fields` list can contain:

- **Model field names** -- e.g. `'name'`, `'active'`
- **Datatable column names** -- columns defined in a `Datatable` inner class on the model
- **Column instances** -- directly instantiated column objects

```python
class Payment(models.Model):
    amount = models.IntegerField()

    class Datatable(DatatableModel):
        currency_amount = CurrencyPenceColumn(column_name='currency_amount', field='amount')

    class ReportBuilder(ReportBuilderFields):
        fields = [
            'date',
            'currency_amount',              # Reference a Datatable column by name
            CustomDateColumn(               # Inline column instance
                column_name='modified',
                field='modified',
                title='Modified',
            ),
        ]
```

## Includes

The `includes` dictionary lets you traverse relationships to include fields from related models. Each key is the relationship name, and the value is a configuration dictionary:

```python
class ReportBuilder(ReportBuilderFields):
    includes = {
        'company': {
            'title': 'Company',
            'model': 'myapp.Company.ReportBuilder',
        },
        'user_profile': {
            'title': 'User',
            'model': 'myapp.UserProfile.ReportBuilder',
            'show_includes': False,   # Don't show nested includes
        },
        'companyinformation': {
            'title': 'Company Information',
            'model': 'myapp.CompanyInformation.ReportBuilder',
            'reversed': True,         # Reverse foreign key
            'allow_pivots': False,    # Disable pivots for this include
        },
    }
```

### Include options

| Key | Type | Default | Description |
|---|---|---|---|
| `title` | `str` | required | Display name in the UI |
| `model` | `str` | required | Dotted path to the related model's `ReportBuilder` class (e.g. `'myapp.Company.ReportBuilder'`) |
| `show_includes` | `bool` | `True` | Whether to show nested includes from the related model |
| `reversed` | `bool` | `False` | Set to `True` for reverse foreign key relationships |
| `allow_pivots` | `bool` | `True` | Whether pivot fields from the related model are available |

## Pivot fields

Pivot fields allow table reports to create dynamic columns based on field values:

```python
class ReportBuilder(ReportBuilderFields):
    @property
    def pivot_fields(self):
        return {
            'tags': {
                'title': 'Tags',
                'type': 'tag',
                'field': 'Tags',
                'kwargs': {'collapsed': False},
            },
            'importance_choice': {
                'title': 'Importance',
                'type': 'pivot',
                'field': 'importance_choice',
                'kwargs': {'collapsed': False},
            },
        }
```

### Pivot field options

| Key | Type | Description |
|---|---|---|
| `title` | `str` | Display name in the UI |
| `type` | `str` | Either `'tag'` or `'pivot'` |
| `field` | `str` | The field name to pivot on |
| `kwargs` | `dict` | Additional keyword arguments (e.g. `{'collapsed': False}`) |
