import base64

from crispy_forms.layout import HTML, Div
from django.conf import settings
from django.utils.module_loading import import_string
from django_datatables.columns import ColumnNameError
from django_datatables.datatables import ColumnInitialisor
from django_modals.helper import show_modal

from advanced_report_builder.exceptions import ReportError


def split_attr(data):
    if 'data_attr' not in data:
        return {}
    _attr = {}
    s = data['data_attr'].split('-')
    _attr.update({s[k]: s[k + 1] for k in range(0, int(len(s) - 1), 2)})
    return _attr


def split_slug(slug_str):
    s = slug_str.split('-')
    slug = {}
    if len(s) == 1:
        slug['pk'] = s[0]
    else:
        slug.update({s[k]: s[k + 1] for k in range(0, int(len(s) - 1), 2)})
    return slug


def make_slug_str(slug, overrides=None):
    if len(slug) == 1 and 'pk' in slug and not overrides:
        return slug['pk']

    if not overrides:
        slug_parts = [f'{k}-{v}' for k, v in slug.items()]
    else:
        slug_parts = []
        for key, value in slug.items():
            if key in overrides:
                continue
            slug_parts.append(f'{key}-{value}')
        for key, value in overrides.items():
            slug_parts.append(f'{key}-{value}')

    return '-'.join(slug_parts)


def get_custom_report_builder():
    return import_string(getattr(settings,
                                 'REPORT_BUILDER_CUSTOMISATION',
                                 'report_builder.customise.CustomiseReportBuilder'))


def get_django_field(base_model, field):

    original_column_initialisor = ColumnInitialisor(start_model=base_model, path=field)

    try:
        columns = original_column_initialisor.get_columns()
    except ColumnNameError as e:
        raise ReportError(e)
    django_field = original_column_initialisor.django_field
    col_type_override = None
    if columns:
        col_type_override = columns[0]
        if isinstance(field, str) and '__' in field and col_type_override.model_path == '':
            # I think there is a bug in datatables where the model path isn't always set! hence the following code
            field_parts = field.split('__')[:-1]
            model_path = '__'.join(field_parts) + '__'
            col_type_override.model_path = model_path
            col_type_override.field = col_type_override.field  # actions the setter

    if django_field is None and columns:
        col_type_override = columns[0]
        if isinstance(col_type_override.field, str):
            if isinstance(field, str):
                path_parts = field.split('__')[:-1]
                path_parts.append(col_type_override.field.split('__')[-1])
                path = '__'.join(path_parts)
                column_initialisor = ColumnInitialisor(start_model=base_model, path=path)
                column_initialisor.get_columns()
                django_field = column_initialisor.django_field
            else:
                column_initialisor = ColumnInitialisor(start_model=base_model, path=col_type_override.field)
                column_initialisor.get_columns()
                django_field = column_initialisor.django_field

    return django_field, col_type_override, columns


def crispy_modal_link_args(modal_name, text, *args, div=False, div_classes='', button_classes='', font_awesome=None):
    link = HTML(show_modal(modal_name, *args, button=text, button_classes=button_classes, font_awesome=font_awesome))
    if div:
        link = Div(link, css_class=div_classes)
    return link


def encode_attribute(string_in):
    _data = string_in.encode('utf-8', 'ignore')
    _data = base64.urlsafe_b64encode(_data).decode('utf-8', 'ignore')
    return _data.replace('-', '@')


def decode_attribute(data_attr):
    data_attr = data_attr.replace('@', '-')
    _data = base64.urlsafe_b64decode(data_attr)
    return _data.decode('utf-8', 'ignore')
