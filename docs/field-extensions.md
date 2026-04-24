# Field extensions

Field extensions let a downstream Django app inject extra form fields into
the **column edit modal** (`TableFieldModal`) and round-trip values through
the column's `data_attr`. The mechanism is opt-in per render, so registering
an extension does **not** affect existing reports — only modals that
explicitly request it will see the extra fields.

Use this when you want per-column configuration that's specific to your app
but logically lives alongside the existing column options (alignment,
decimal places, filter, etc.). A typical example is letting an administrator
mark a column as "allow filtering via a GET parameter" in an API endpoint.

## How it works

1. A downstream app defines a subclass of
   `advanced_report_builder.field_extensions.FieldExtension` and registers
   it in settings under a short key.
2. A modal that wants the extra fields appends `-extensions-<key>` to the
   `select_column_url` slug it hands to the column picker.
3. When the column edit modal is opened from that picker, ARB loads the
   matching extension class and calls it from three places: when setting up
   form fields, when building the crispy layout, and when serialising back
   to `data_attr`.
4. Modals that do **not** include an `extensions-` segment in their slug
   see no extensions — behaviour is unchanged.

## The extension interface

Subclass `FieldExtension` and implement whichever methods you need. All
methods are optional:

```python
from advanced_report_builder.field_extensions import FieldExtension


class MyExtension(FieldExtension):
    key = 'my_extension'

    def applies_to(self, django_field, col_type_override, data):
        """Return True to activate for this field, False to skip."""
        return django_field is not None

    def add_form_fields(self, form, data_attr):
        """Mutate `form.fields` to add extension fields and load initial
        values from the column's existing `data_attr` dict."""

    def layout(self):
        """Return a list of crispy layout elements to append after the
        base layout. Only consulted when the base layout is a custom one
        (currency, number, link, reverse-FK columns). For default-layout
        columns, `add_form_fields` is enough -- the new fields render in
        field order."""
        return None

    def save_attributes(self, form, attributes):
        """Append hyphen-joined `data_attr` entries to the list. Values
        that may contain unsafe characters should go through
        `advanced_report_builder.utils.encode_attribute`."""
```

## Registering the extension

Register the extension in your Django settings under its short key:

```python
ADVANCED_REPORT_BUILDER_FIELD_EXTENSIONS = {
    'my_extension': 'myapp.arb_extensions.MyExtension',
}
```

The key is the short name you'll reference from the slug. Multiple
extensions can be registered and activated independently.

## Activating the extension on a specific modal

The modal that owns the column picker needs to opt in by appending
`extensions-<key>` to its `select_column_url` slug:

```python
url = reverse(
    'advanced_report_builder:table_field_modal',
    kwargs={
        'slug': (
            'selector-99999'
            '-data-FIELD_INFO'
            '-report_type_id-REPORT_TYPE_ID'
            '-extensions-my_extension'
        ),
    },
)
```

To activate multiple extensions on the same modal, comma-separate the keys:

```
...-extensions-my_extension,another_extension
```

Only modals that include `extensions-...` in their slug receive the extra
fields. The built-in report-builder and dashboard modals do not, so
existing reports are unaffected.

## Worked example

A downstream app wants to mark any column as "filterable via a GET query
parameter" with a configurable operator.

**`myapp/arb_extensions.py`**

```python
from advanced_report_builder.field_extensions import FieldExtension
from advanced_report_builder.toggle import RBToggle
from advanced_report_builder.utils import decode_attribute, encode_attribute
from django.forms import BooleanField, CharField


class FilterableExtension(FieldExtension):
    key = 'filterable'

    def applies_to(self, django_field, col_type_override, data):
        return django_field is not None

    def add_form_fields(self, form, data_attr):
        form.fields['filter_enabled'] = BooleanField(
            required=False, widget=RBToggle(), label='Allow GET filtering'
        )
        form.fields['filter_param'] = CharField(
            required=False, label='Query param',
        )
        if data_attr.get('filter_enabled') == '1':
            form.fields['filter_enabled'].initial = True
        if 'filter_param' in data_attr:
            form.fields['filter_param'].initial = decode_attribute(data_attr['filter_param'])

    def save_attributes(self, form, attributes):
        if not form.cleaned_data.get('filter_enabled'):
            return
        attributes.append('filter_enabled-1')
        param = (form.cleaned_data.get('filter_param') or '').strip()
        if param:
            attributes.append(f'filter_param-{encode_attribute(param)}')
```

**settings.py**

```python
ADVANCED_REPORT_BUILDER_FIELD_EXTENSIONS = {
    'filterable': 'myapp.arb_extensions.FilterableExtension',
}
```

**The owning modal**

```python
url = reverse(
    'advanced_report_builder:table_field_modal',
    kwargs={'slug': 'selector-99999-data-FIELD_INFO-report_type_id-REPORT_TYPE_ID-extensions-filterable'},
)
```

Reading the saved values back at request time:

```python
from advanced_report_builder.utils import decode_attribute, split_attr

for column in api_report.columns:
    attrs = split_attr(column)
    if attrs.get('filter_enabled') == '1':
        param = decode_attribute(attrs['filter_param'])
        # ...apply queryset filter using request.GET[param]...
```

## Guarantees

- When `ADVANCED_REPORT_BUILDER_FIELD_EXTENSIONS` is absent or empty, ARB
  behaves exactly as it did before extensions existed.
- When the setting is populated but the modal's slug has no `extensions-`
  segment, the column edit modal renders with no extension fields and
  saves no extension keys into `data_attr`.
- Unknown extension keys in a slug are silently ignored, so typos cannot
  break the modal.
- `data_attr` keys that an extension writes are preserved verbatim when
  the column is edited again — the column-list JavaScript does not inspect
  key names.
