"""Pluggable field-editor extensions for TableFieldModal.

An extension can inject extra form fields / crispy layout pieces into the
column edit modal and round-trip values through the column's data_attr.

Activation is opt-in *per render*: the consuming modal appends
``-extensions-<key>`` to the ``select_column_url`` slug. Modals that don't
specify an ``extensions`` segment (i.e. every existing use) get no extensions.
"""

from django.conf import settings
from django.utils.module_loading import import_string


class FieldExtension:
    key = None

    def applies_to(self, django_field, col_type_override, data):
        return True

    def add_form_fields(self, form, data_attr):
        pass

    def layout(self):
        return None

    def save_attributes(self, form, attributes):
        pass


def load_field_extensions(slug):
    raw = (slug or {}).get('extensions')
    if not raw:
        return []
    keys = [k for k in raw.split(',') if k]
    registry = getattr(settings, 'ADVANCED_REPORT_BUILDER_FIELD_EXTENSIONS', None) or {}
    result = []
    for k in keys:
        dotted = registry.get(k)
        if dotted:
            result.append(import_string(dotted)())
    return result
