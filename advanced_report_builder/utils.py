import base64

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
