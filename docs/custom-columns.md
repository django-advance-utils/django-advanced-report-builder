# Custom columns

The report builder provides several column classes for common display patterns. These can be used in Datatable inner classes and referenced from the `ReportBuilder.fields` list.

## Built-in column classes

### ReportBuilderDateColumn

Formats date values with a configurable format string.

```python
from advanced_report_builder.columns import ReportBuilderDateColumn

class Datatable(DatatableModel):
    created_date = ReportBuilderDateColumn(
        column_name='created_date',
        field='created',
        title='Created',
        date_format='%d/%m/%Y',  # Optional, defaults to '%d/%m/%Y'
    )
```

### ReportBuilderNumberColumn

Formats numeric values with configurable decimal places.

```python
from advanced_report_builder.columns import ReportBuilderNumberColumn

class Datatable(DatatableModel):
    weight = ReportBuilderNumberColumn(
        column_name='weight',
        field='weight',
        title='Weight',
        decimal_places=2,
        trim_zeros=True,  # Remove trailing zeros (default: True)
    )
```

### ReportBuilderCurrencyColumn

Formats values as currency (whole units).

```python
from advanced_report_builder.columns import ReportBuilderCurrencyColumn
```

### ReportBuilderCurrencyPenceColumn

Formats values stored in pence/cents and displays as currency (divides by 100).

```python
from advanced_report_builder.columns import ReportBuilderCurrencyPenceColumn
```

### ColourColumn

Displays a colour swatch based on a hex colour value stored in the model.

```python
from advanced_report_builder.columns import ColourColumn

class Datatable(DatatableModel):
    background_colour_column = ColourColumn(
        title='Background Colour',
        field='background_colour',
    )
```

### ArrowColumn

Displays a right-arrow icon. Useful as a navigation indicator in table rows.

```python
from advanced_report_builder.columns import ArrowColumn

class Datatable(DatatableModel):
    arrow = ArrowColumn(title='Arrow Icon')
```

### FilterForeignKeyColumn

A column that provides filter options derived from distinct values of a foreign key field.

```python
from advanced_report_builder.columns import FilterForeignKeyColumn

class Datatable(DatatableModel):
    category = FilterForeignKeyColumn(
        field='company_category__name',
        title='Category',
    )
```

### RecordCountColumn

Adds a count annotation to the queryset. Automatically included in the default `field_classes` as `'record_count'`.

```python
from advanced_report_builder.columns import RecordCountColumn
```

### ReportBuilderColumnLink

A clickable link column that can link to a Django URL.

```python
from advanced_report_builder.columns import ReportBuilderColumnLink

class Datatable(DatatableModel):
    link = ReportBuilderColumnLink(
        title='View',
        field='name',
        url_name='myapp:detail',
    )

    # With a custom link template and multiple fields
    link2 = ReportBuilderColumnLink(
        title='Edit',
        field=['id', 'name'],
        url_name='myapp:edit',
        width='10px',
        link_html='<button class="btn btn-sm btn-outline-dark"><i class="fas fa-edit"></i></button>',
    )
```

Links are automatically disabled when `enable_links` is not set on the view (e.g. for wall-board displays).

### ReportBuilderManyToManyColumn

Displays values from a many-to-many relationship.

```python
from advanced_report_builder.columns import ReportBuilderManyToManyColumn

class Datatable(DatatableModel):
    sector_names = ReportBuilderManyToManyColumn(field='sectors__name')
```

## Reverse foreign key columns

These columns aggregate data from reverse foreign key relationships.

### ReverseForeignKeyStrColumn

Aggregates string values from a reverse FK using `StringAgg`.

```python
from advanced_report_builder.columns import ReverseForeignKeyStrColumn

class Datatable(DatatableModel):
    contract_notes = ReverseForeignKeyStrColumn(
        field_name='contract__notes',
        report_builder_class_name='myapp.Contract.ReportBuilder',
    )
```

### ReverseForeignKeyBoolColumn

Aggregates boolean values from a reverse FK using XOR, AND or Array operations.

```python
from advanced_report_builder.columns import ReverseForeignKeyBoolColumn

class Datatable(DatatableModel):
    contract_valid = ReverseForeignKeyBoolColumn(
        field_name='contract__valid',
        report_builder_class_name='myapp.Contract.ReportBuilder',
    )
```

### ReverseForeignKeyChoiceColumn

Aggregates choice field values from a reverse FK.

```python
from advanced_report_builder.columns import ReverseForeignKeyChoiceColumn

class Datatable(DatatableModel):
    contract_temperature = ReverseForeignKeyChoiceColumn(
        field_name='contract__temperature',
        report_builder_class_name='myapp.Contract.ReportBuilder',
    )
```

### ReverseForeignKeyDateColumn

Aggregates date values from a reverse FK using Array, Min or Max operations.

```python
from advanced_report_builder.columns import ReverseForeignKeyDateColumn

class Datatable(DatatableModel):
    contract_created = ReverseForeignKeyDateColumn(
        field_name='contract__created',
        report_builder_class_name='myapp.Contract.ReportBuilder',
    )
```

## Delimiter options

Reverse foreign key string and date array columns support configurable delimiters:

| Delimiter | Display |
|---|---|
| Comma | `, ` |
| Semicolon | `;` |
| Pipe | ` \| ` |
| Dash | ` - ` |
| Space | ` ` |
