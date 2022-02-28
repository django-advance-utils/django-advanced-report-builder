import re

from django.apps import apps

from advanced_report_builder.utils import get_django_field


def get_menu_fields(base_model, report_builder_class, menus=None, codes=None, code_prefix='', previous_base_model=None):

    for report_builder_field in report_builder_class.fields:
        django_field, col_type_override, columns = get_django_field(base_model=base_model,
                                                                    field=report_builder_field)
        for column in columns:
            full_id = code_prefix + column.column_name
            if menus is not None:
                menus.append({'code': full_id, 'text': column.title})
            if codes is not None:
                codes.add(full_id)

    for include in report_builder_class.includes:
        app_label, model, report_builder_fields_str = include['model'].split('.')

        new_model = apps.get_model(app_label, model)
        if new_model != previous_base_model:
            new_report_builder_class = getattr(new_model, report_builder_fields_str, None)
            title = new_report_builder_class.title
            if menus is not None:
                menu = []
            else:
                menu = None
            get_menu_fields(base_model=new_model,
                            report_builder_class=new_report_builder_class,
                            menus=menu,
                            codes=codes,
                            code_prefix=f"{code_prefix}{include['field']}__",
                            previous_base_model=base_model)
            if menus is not None:
                menus.append({'text': title, 'menu': menu})


def get_data_merge_columns(base_model, report_builder_class, html):
    display_fields = set()
    all_fields = set()

    get_menu_fields(base_model=base_model,
                    report_builder_class=report_builder_class,
                    codes=display_fields)

    variables = re.findall('{{\s*([^*\s*}}]+)\s*}}', html)
    columns = set()
    for variable in variables:
        if '|' in variable:
            field = variable.split('|')[0]
        elif '&' in variable:
            field = variable.split('&')[0]
        else:
            field = variable
        all_fields.add(field)
        if field in display_fields:
            columns.add('.' + field)

    variables = re.findall('{%\s*if\s([^%}]+)\s*%}', html)

    for variable in variables:
        for field in variable.split(' '):

            if field not in ['', 'not', 'and' 'or'] and field[0] not in ['=', '<', '>', '(', ')', '"', "'"]:
                all_fields.add(field)
                if field not in display_fields:
                    columns.add('.' + field)

    column_map = {}
    for field in all_fields:
        _, col_type_override, _ = get_django_field(base_model=base_model, field=field)
        field_parts = field.split('__')

        if col_type_override is not None and field_parts[-1] != col_type_override.field:
            column_map[field] = col_type_override.field
    return columns, column_map




