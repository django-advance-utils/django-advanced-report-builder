from django.conf import settings
from django.utils.module_loading import import_string


def split_attr(data):
    if 'data_attr' not in data:
        return None
    _attr = {}
    s = data['data_attr'].split('-')
    _attr.update({s[k]: s[k + 1] for k in range(0, int(len(s) - 1), 2)})
    return _attr


def get_custom_report_builder():
    return import_string(getattr(settings,
                                 'REPORT_BUILDER_CUSTOMISATION',
                                 'report_builder.customise.CustomiseReportBuilder'))
