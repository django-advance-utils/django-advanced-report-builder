import re

from django.apps import apps

from advanced_report_builder.field_utils import ReportBuilderFieldUtils
from advanced_report_builder.utils import get_report_builder_class

_COLON_KEY_RE = re.compile(r'^([A-Za-z][A-Za-z0-9]*)\s*:\s*(.+)$')


def normalize_data_merge_key(key):
    """Translate JMS Pro's ``{ Model: field }`` colon form into a dotted path.

    The identifier is slugified the way Pro does (``GlassSpacer`` -> ``glass_spacer``) and joined
    to the field, e.g. ``Glass: code`` -> ``glass.code`` / ``GlassSpacer: width`` ->
    ``glass_spacer.width``. Plain dotted keys (``project.name``) are returned unchanged.
    """
    key = (key or '').strip()
    match = _COLON_KEY_RE.match(key)
    if not match:
        return key
    identifier, field = match.group(1), match.group(2).strip()
    slug = '_'.join(re.findall('[A-Z][^A-Z]*', identifier)).lower() or identifier.lower()
    return f'{slug}.{field}'


class DataMergeUtils(ReportBuilderFieldUtils):
    def get_menu_fields(
        self,
        base_model,
        report_builder_class,
        menus=None,
        codes=None,
        code_prefix='',
        next_code_prefix='__',
        previous_base_model=None,
        table=None,
        show_includes=True,
        colon_includes=False,
    ):
        for report_builder_field in report_builder_class.fields:
            django_field, col_type_override, columns, _ = self.get_field_details(
                base_model=base_model,
                field=report_builder_field,
                report_builder_class=report_builder_class,
                table=table,
            )
            for column in columns:
                full_id = code_prefix + column.column_name
                if column.title != '':
                    if menus is not None:
                        menus.append({'code': full_id, 'text': column.title})
                    if codes is not None:
                        codes.add(full_id)
        if show_includes:
            for include_field, include in report_builder_class.includes.items():
                app_label, model, report_builder_fields_str = include['model'].split('.')

                new_model = apps.get_model(app_label, model)
                if new_model != previous_base_model:
                    new_report_builder_class = get_report_builder_class(
                        model=new_model, class_name=report_builder_fields_str
                    )

                    title = include.get('title')
                    if title is None or title == '':
                        title = new_report_builder_class.title
                    menu = [] if menus is not None else None
                    self.get_menu_fields(
                        base_model=new_model,
                        report_builder_class=new_report_builder_class,
                        menus=menu,
                        codes=codes,
                        code_prefix=f'{code_prefix}{include_field}{next_code_prefix}',
                        next_code_prefix=next_code_prefix,
                        previous_base_model=base_model,
                        table=table,
                        show_includes=include.get('show_includes', True),
                    )
                    if menus is not None:
                        if colon_includes:
                            # JMS Pro look: a related model's own fields insert as the colon form
                            # ``{ Model: field }`` (round-trips through normalize_data_merge_key).
                            # Only this include's direct leaf fields; nested includes stay dotted.
                            identifier = ''.join(word.title() for word in include_field.split('_'))
                            prefix = f'{code_prefix}{include_field}{next_code_prefix}'
                            for item in menu:
                                if 'code' in item and item['code'].startswith(prefix):
                                    item['colon'] = f'{identifier}: {item["code"][len(prefix):]}'
                        menus.append({'text': title, 'menu': menu})

    # Characters allowed inside a JMS Pro single-brace ``{ }`` tag (mirrors the grammar in
    # ``core.libraries.data_merge_parser.DataMergeParser``).
    _PRO_TAG_RE = re.compile(r'\{ *([A-Za-z0-9_:&%\-+*/.; ()|=@!]+?) *\}')
    # The alt ``{[ ]}`` form (Pro's second-pass tags).
    _PRO_ALT_TAG_RE = re.compile(r'\{\[ *([A-Za-z0-9_:&%\-+*/.; ()|=@!]+?) *\]\}')
    _PRO_OPERATOR_RE = re.compile(r'\||&amp;&amp;|&&|@[-+*/]@')
    _PRO_PATH_RE = re.compile(r'^[A-Za-z0-9_.]+$')

    @classmethod
    def get_data_merge_variables(cls, html):
        all_fields = set()

        # Legacy Django ``{{ }}`` / ``{% if %}`` tags (resolved during the dual-parse window).
        variables = re.findall(r'{{\s*([^*\s*}}]+)\s*}}', html)
        for variable in variables:
            if '|' in variable:
                field = variable.split('|')[0]
            elif '&' in variable:
                field = variable.split('&')[0]
            else:
                field = variable
            all_fields.add(field)

        variables = re.findall(r'{%\s*(if|elif|with)\s([^%}]+)\s*%}', html)
        for variable in variables:
            for field in variable[1].split(' '):
                if field != '' and (field == 'as' or field[0] in ['=', '<', '>']):
                    break
                if field not in ['', 'not', 'andor'] and field[0] not in [
                    '(',
                    ')',
                    '"',
                    "'",
                ]:
                    all_fields.add(field)

        # JMS Pro single-brace ``{ field }`` and alt ``{[ field ]}`` tags, including those nested
        # inside ``{% %}`` / ``{[% %]}`` conditionals. Split off multi/fallback (``|``, ``&&``) and
        # maths (``@x@``) operators, normalise the colon ``Model: field`` form to a dotted path,
        # and keep only dotted field paths (literals are ignored for column fetching).
        for content in cls._PRO_TAG_RE.findall(html) + cls._PRO_ALT_TAG_RE.findall(html):
            for token in cls._PRO_OPERATOR_RE.split(content):
                token = normalize_data_merge_key(token.strip().lstrip('!').strip())
                if token and cls._PRO_PATH_RE.match(token):
                    all_fields.add(token)
        return all_fields

    def get_data_merge_columns(self, base_model, report_builder_class, html, table):
        all_fields = self.get_data_merge_variables(html)
        columns = set()
        column_map = {}
        for field in all_fields:
            django_field, col_type_override, _, _ = self.get_field_details(
                base_model=base_model,
                field=field,
                report_builder_class=report_builder_class,
                table=table,
            )
            if django_field is not None or isinstance(col_type_override.field, list | tuple):
                if field not in columns and f'.{field}' not in columns:
                    columns.add('.' + field)

                field_parts = field.split('__')

                if col_type_override is not None and field_parts[-1] != col_type_override.field:
                    column_map[field] = col_type_override.field
        return columns, column_map
