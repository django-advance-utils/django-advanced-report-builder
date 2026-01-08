import base64
from datetime import date, timedelta

from crispy_forms.layout import HTML, Div
from django.conf import settings
from django.utils.module_loading import import_string
from django_modals.helper import show_modal


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


def make_slug_str(slug, overrides=None, excludes=None):
    overrides = overrides or {}
    excludes = set(excludes or [])

    if len(slug) == 1 and 'pk' in slug and not overrides:
        return slug['pk']

    # 1. Start from base slug
    final = {k: v for k, v in slug.items() if k not in excludes}

    # 2. Apply overrides (replace or add)
    for k, v in overrides.items():
        if k not in excludes:
            final[k] = v

    # 3. Serialize
    return '-'.join(f'{k}-{v}' for k, v in final.items())


def get_custom_report_builder():
    return import_string(
        getattr(
            settings,
            'REPORT_BUILDER_CUSTOMISATION',
            'report_builder.customise.CustomiseReportBuilder',
        )
    )


def crispy_modal_link_args(
    modal_name,
    text,
    *args,
    div=False,
    div_classes='',
    button_classes='',
    font_awesome=None,
):
    link = HTML(
        show_modal(
            modal_name,
            *args,
            button=text,
            button_classes=button_classes,
            font_awesome=font_awesome,
        )
    )
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


def get_report_builder_class(model, report_type=None, class_name=None):
    if class_name is None:
        class_name = report_type.report_builder_class_name

    report_builder_class = getattr(model, class_name, None)
    if report_builder_class is not None:
        report_builder_class = report_builder_class()
    return report_builder_class


def get_query_js(button_name, field_id):
    return (
        'django_modal.process_commands_lock([{"function": "post_modal", "button": {"button": "'
        + button_name
        + '", "'
        + field_id
        + "\": $(this).closest('tr').attr('id')}}])"
    )


def count_days(
    start_date: date, end_date: date, exclude_weekdays: list[int] = None, exclude_dates: list[date] = None
) -> int:
    if start_date > end_date:
        start_date, end_date = end_date, start_date

    exclude_weekdays = set(exclude_weekdays or [])
    exclude_dates = set(exclude_dates or [])

    current = start_date
    count = 0
    while current < end_date:
        weekday = ((current.weekday() + 1) % 7) + 1  # Django-style Sunday=1
        if weekday not in exclude_weekdays and current not in exclude_dates:
            count += 1
        current += timedelta(days=1)
    return count


def excel_column_name(n: int, row: int | None = None) -> str:
    """Convert a 1-based column index to an Excel column name, with optional row."""
    col = []
    c = n
    while c > 0:
        c -= 1
        col.append(chr((c % 26) + ord('A')))
        c //= 26
    col = ''.join(reversed(col))

    if row is not None:
        return f'{col}{row}'
    return col


def try_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def get_view_type_class():
    cls_path = getattr(
        settings,
        'REPORT_BUILDER_VIEW_TYPES_CLASS',
        'advanced_report_builder.view_types.ViewTypes',
    )
    cls = import_string(cls_path)
    return cls()


def get_template_type_class():
    cls_path = getattr(
        settings,
        'REPORT_BUILDER_TEMPLATE_TYPES_CLASS',
        'advanced_report_builder.template_types.TemplateTypes',
    )
    cls = import_string(cls_path)
    return cls()
