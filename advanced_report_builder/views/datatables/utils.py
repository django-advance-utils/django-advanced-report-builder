import copy
import json

from django.db.models import ExpressionWrapper, F, FloatField, Q
from django.db.models.functions import NullIf
from django.template import Context, Template, TemplateSyntaxError
from django_datatables.columns import ColumnBase
from django_datatables.helpers import render_replace
from django_datatables.plugins.column_totals import ColumnTotals

from advanced_report_builder.column_types import (
    CURRENCY_COLUMNS,
    DATE_FIELDS,
    LINK_COLUMNS,
    NUMBER_FIELDS,
    REVERSE_FOREIGN_KEY_BOOL_COLUMNS,
    REVERSE_FOREIGN_KEY_CHOICE_COLUMNS,
    REVERSE_FOREIGN_KEY_DATE_COLUMNS,
    REVERSE_FOREIGN_KEY_STR_COLUMNS,
)
from advanced_report_builder.columns import ReportBuilderDateColumn
from advanced_report_builder.globals import (
    ALIGNMENT_CHOICE_RIGHT,
    ALIGNMENT_CLASS,
    ANNOTATION_CHOICE_NA,
    ANNOTATION_VALUE_FUNCTIONS,
    DATE_FORMAT_TYPE_DD_MM_YY_SLASH,
    DATE_FORMAT_TYPES_DJANGO_FORMAT,
    REVERSE_FOREIGN_KEY_ANNOTATION_BOOLEAN_XOR,
    REVERSE_FOREIGN_KEY_DELIMITER_COMMA,
)
from advanced_report_builder.utils import decode_attribute, split_attr
from advanced_report_builder.views.report_utils_mixin import ReportUtilsMixin


class TableUtilsMixin(ReportUtilsMixin):
    date_field = ReportBuilderDateColumn
    column_totals_class = ColumnTotals

    def __init__(self, *args, **kwargs):
        self.table_report = None
        super().__init__(*args, **kwargs)

    def get_date_field(self, index, col_type_override, table_field, fields):
        data_attr = split_attr(table_field)
        field_name = table_field['field']
        date_format = data_attr.get('date_format')

        if date_format:
            date_format = DATE_FORMAT_TYPES_DJANGO_FORMAT.get(int(date_format))

        if int(data_attr.get('display_heading', 1)) == 0:
            display_heading = False
            title = ''
        else:
            display_heading = True
            title = table_field.get('title')

        annotations_value = int(data_attr.get('annotations_value', 0))
        if col_type_override and annotations_value == 0:
            col_type_override.table = None
            field = copy.deepcopy(col_type_override)
            if title or not display_heading:
                field.title = title
            fields.append(field)
        else:
            if col_type_override:
                field_name = col_type_override.field
            date_function_kwargs = {'title': title, 'date_format': date_format}

            if annotations_value != 0:
                new_field_name = f'{annotations_value}_{field_name}_{index}'
                new_field_name = new_field_name.replace('__', '_')
                function = ANNOTATION_VALUE_FUNCTIONS[annotations_value]
                date_function_kwargs['annotations_value'] = {new_field_name: function(field_name)}
                field_name = new_field_name

            date_function_kwargs.update({'field': field_name, 'column_name': field_name})

            field = self.date_field(**date_function_kwargs)
            fields.append(field)

        return field_name

    @staticmethod
    def get_link_field(table_field, fields, col_type_override):
        field_name = table_field['field']
        col_type_override.table = None
        field = copy.deepcopy(col_type_override)
        data_attr = split_attr(table_field)
        link_css = ''
        if 'link_css' in data_attr:
            link_css = decode_attribute(data_attr['link_css'])

        link_html = ''
        if 'link_html' in data_attr:
            link_html = decode_attribute(data_attr['link_html'])

        if link_css or link_html:
            field.setup_link(link_css=link_css, link_html=link_html)

        is_icon = data_attr.get('is_icon')
        if is_icon == '1':
            field.title = ''
            field.options['no_col_search'] = True
            field.column_defs['orderable'] = False
            field.column_defs['width'] = '10px'

        elif 'title' in table_field:
            field.title = table_field['title']
        fields.append(field)

        return field_name

    def process_query_results(
        self,
        report_builder_class,
        table,
        base_model,
        fields_used,
        fields_map,
        table_fields,
        pivot_fields=None,
    ):
        first_field_name = None

        field_name = None
        fields = []
        totals = {}

        has_annotations = False
        if not table_fields:
            return fields, totals, first_field_name

        for index, table_field in enumerate(table_fields):
            field = table_field['field']
            field_attr = {}
            if 'title' in table_field:
                field_attr['title'] = table_field['title']

            original_field_name = field
            fields_used.add(field)
            django_field, col_type_override, _, _ = self.get_field_details(
                base_model=base_model,
                field=field,
                table=table,
                report_builder_class=report_builder_class,
                field_attr=field_attr,
            )

            data_attr = split_attr(table_field)
            if int(data_attr.get('display_heading', 1)) == 0:
                field_attr['title'] = ''

            annotations_type = int(data_attr.get('annotations_type', 0))
            append_annotation_query = int(data_attr.get('append_annotation_query', 0))

            if annotations_type != 0 or append_annotation_query != 0:
                has_annotations = True

            if isinstance(django_field, DATE_FIELDS):
                field_name = self.get_date_field(
                    index=index,
                    col_type_override=col_type_override,
                    table_field=table_field,
                    fields=fields,
                )
            elif isinstance(django_field, NUMBER_FIELDS) and (django_field is None or django_field.choices is None):
                decimal_places = data_attr.get('decimal_places')
                append_annotation_query = int(data_attr.get('append_annotation_query', 0)) == 1

                field_name = self.get_number_fields(
                    field_name=field_name,
                    table=table,
                    base_model=base_model,
                    report_builder_class=report_builder_class,
                    annotations_type=annotations_type,
                    append_annotation_query=append_annotation_query,
                    index=index,
                    data_attr=data_attr,
                    table_field=table_field,
                    fields=fields,
                    totals=totals,
                    col_type_override=col_type_override,
                    decimal_places=decimal_places,
                )

            elif isinstance(col_type_override, REVERSE_FOREIGN_KEY_STR_COLUMNS):
                field_name = table_field['field']
                field = self.get_reverse_foreign_key_str_field(
                    col_type_override=col_type_override,
                    data_attr=data_attr,
                    field_attr=field_attr,
                    index=index,
                )
                fields.append(field)
            elif isinstance(col_type_override, REVERSE_FOREIGN_KEY_BOOL_COLUMNS):
                field_name = table_field['field']
                field = self.get_reverse_foreign_key_bool_field(
                    col_type_override=col_type_override,
                    data_attr=data_attr,
                    field_attr=field_attr,
                    index=index,
                )
                fields.append(field)
            elif isinstance(col_type_override, REVERSE_FOREIGN_KEY_CHOICE_COLUMNS):
                field_name = table_field['field']
                field = self.get_reverse_foreign_key_choice_field(
                    col_type_override=col_type_override,
                    data_attr=data_attr,
                    field_attr=field_attr,
                    index=index,
                )
                fields.append(field)

            elif isinstance(col_type_override, REVERSE_FOREIGN_KEY_DATE_COLUMNS):
                field_name = table_field['field']
                field = self.get_reverse_foreign_key_date_field(
                    col_type_override=col_type_override,
                    data_attr=data_attr,
                    field_attr=field_attr,
                    index=index,
                )
                fields.append(field)

            elif isinstance(col_type_override, LINK_COLUMNS):
                field_name = self.get_link_field(
                    table_field=table_field,
                    col_type_override=col_type_override,
                    fields=fields,
                )

            elif django_field is None and table_field['field'] in [
                'rb_addition',
                'rb_subtraction',
                'rb_times',
                'rb_division',
                'rb_percentage',
            ]:
                self.setup_mathematical_field(
                    data_attr=data_attr,
                    fields=fields,
                    field_attr=field_attr,
                    table_field=table_field,
                    col_type_override=col_type_override,
                    index=index,
                    totals=totals,
                )
            else:
                if col_type_override is not None and data_attr.get('annotation_label') == '1':
                    if isinstance(col_type_override.field, list):
                        table.initial_values += col_type_override.field
                    else:
                        table.initial_values.append(col_type_override.field)

                field_name = field
                if isinstance(col_type_override, CURRENCY_COLUMNS) and totals is not None:
                    annotations_type = int(data_attr.get('annotations_type', 0))
                    append_annotation_query = int(data_attr.get('append_annotation_query', 0)) == 1
                    field_name = self.get_number_fields(
                        field_name=field_name,
                        table=table,
                        base_model=base_model,
                        report_builder_class=report_builder_class,
                        annotations_type=annotations_type,
                        append_annotation_query=append_annotation_query,
                        index=index,
                        data_attr=data_attr,
                        table_field=table_field,
                        fields=fields,
                        totals=totals,
                        col_type_override=col_type_override,
                        decimal_places=2,
                    )

                elif col_type_override.annotations is not None:
                    css_class = col_type_override.column_defs.get('className')
                    show_total = data_attr.get('show_totals')
                    if show_total == '1':
                        self.set_annotation_total(
                            totals=totals,
                            field_name=field_name,
                            col_type_override=col_type_override,
                            decimal_places=2,
                            css_class=css_class,
                        )
                    if field_attr:
                        field = (field, field_attr)
                        fields.append(field)
                else:
                    if field_attr:
                        field = (field, field_attr)
                    fields.append(field)

            if not first_field_name:
                first_field_name = field_name
            fields_map[original_field_name] = field_name

        if not has_annotations and len(report_builder_class.default_columns) > 0:
            table.add_columns(*report_builder_class.default_columns)
        table.add_columns(*fields)
        table.show_pivot_table = False
        if pivot_fields is not None:
            for pivot_field in pivot_fields:
                pivot_field_data = self._get_pivot_details(
                    base_model=base_model,
                    pivot_str=pivot_field['field'],
                    report_builder_class=report_builder_class,
                )
                if pivot_field_data is None:
                    continue

                if pivot_field_data['id'] not in fields_used:
                    table.add_columns('.' + pivot_field_data['id'])
                    fields_used.add(pivot_field_data['id'])

                pivot_field_details = pivot_field_data['details']
                table.add_js_filters(
                    pivot_field_details['type'],
                    pivot_field_data['id'],
                    filter_title=pivot_field_details['title'],
                    **pivot_field_details['kwargs'],
                )
                table.show_pivot_table = True
        if totals:
            totals[first_field_name] = {'text': 'Totals'}
            table.add_plugin(self.column_totals_class, totals)

    def get_number_fields(
        self,
        field_name,
        table,
        base_model,
        report_builder_class,
        annotations_type,
        append_annotation_query,
        index,
        data_attr,
        table_field,
        fields,
        totals,
        col_type_override,
        decimal_places,
    ):
        if (annotations_type != ANNOTATION_CHOICE_NA or append_annotation_query) and data_attr.get(
            'multiple_columns'
        ) == '1':
            query = self.extra_filters(query=table.model.objects)
            multiple_column_field = data_attr.get('multiple_column_field')

            field_report_builder_class = self._get_report_builder_class(
                base_model=base_model,
                field_str=multiple_column_field,
                report_builder_class=report_builder_class,
            )
            _fields = field_report_builder_class.default_multiple_column_fields
            default_multiple_column_fields = [multiple_column_field + '__' + x for x in _fields]
            order_by = f'{multiple_column_field}__{field_report_builder_class.default_multiple_pk}'

            results = (
                query.order_by(order_by)
                .distinct(multiple_column_field)
                .values(multiple_column_field, *default_multiple_column_fields)
            )

            for multiple_index, result in enumerate(results):
                suffix = self._set_multiple_title(
                    database_values=result,
                    value_prefix=multiple_column_field,
                    fields=_fields,
                    text=field_report_builder_class.default_multiple_column_text,
                )
                extra_filter = Q((multiple_column_field, result[multiple_column_field]))

                field_name = self.get_number_field(
                    annotations_type=annotations_type,
                    append_annotation_query=append_annotation_query,
                    index=f'{index}_{multiple_index}',
                    data_attr=data_attr,
                    table_field=table_field,
                    fields=fields,
                    totals=totals,
                    col_type_override=col_type_override,
                    extra_filter=extra_filter,
                    title_suffix=suffix,
                    decimal_places=decimal_places,
                )
        else:
            field_name = self.get_number_field(
                annotations_type=annotations_type,
                append_annotation_query=append_annotation_query,
                index=index,
                data_attr=data_attr,
                table_field=table_field,
                fields=fields,
                totals=totals,
                col_type_override=col_type_override,
                decimal_places=decimal_places,
            )
        return field_name

    @staticmethod
    def _set_multiple_title(database_values, value_prefix, fields, text):
        results = {}
        for field in fields:
            value = database_values[value_prefix + '__' + field]
            results[field] = value
        return text.format(**results)

    def extra_filters(self, query):
        report_query = self.get_report_query(report=self.table_report)
        if report_query:
            query = self.process_query_filters(query=query, search_filter_data=report_query.query)
        return query

    def setup_mathematical_field(
        self,
        data_attr,
        fields,
        field_attr,
        table_field,
        col_type_override,
        index,
        totals,
    ):
        field = table_field['field']
        if field == 'rb_percentage':
            self.get_mathematical_percentage_field(
                fields=fields,
                field_attr=field_attr,
                data_attr=data_attr,
                table_field=table_field,
                index=index,
                totals=totals,
            )
        elif field == 'rb_division':
            values = self.decode_mathematical_columns(
                data_attr=data_attr,
                first_value_column_name='numerator_column',
                second_value_column_name='denominator_column',
            )
            if values is not None:
                expression = ExpressionWrapper(NullIf(F(values[0]), 0) / F(values[1]), output_field=FloatField())
                self.get_mathematical_field(
                    fields=fields,
                    field_attr=field_attr,
                    data_attr=data_attr,
                    table_field=table_field,
                    col_type_override=col_type_override,
                    index=index,
                    totals=totals,
                    expression=expression,
                )
        elif field == 'rb_times':
            values = self.decode_mathematical_columns(
                data_attr=data_attr,
                first_value_column_name='multiplicand_column',
                second_value_column_name='multiplier_column',
            )
            if values is not None:
                expression = ExpressionWrapper(NullIf(F(values[0]), 0) * F(values[1]), output_field=FloatField())
                self.get_mathematical_field(
                    fields=fields,
                    field_attr=field_attr,
                    data_attr=data_attr,
                    table_field=table_field,
                    col_type_override=col_type_override,
                    index=index,
                    totals=totals,
                    expression=expression,
                )
        elif field == 'rb_addition':
            values = self.decode_mathematical_columns(data_attr=data_attr)
            if values is not None:
                expression = ExpressionWrapper(NullIf(F(values[0]), 0) + F(values[1]), output_field=FloatField())
                self.get_mathematical_field(
                    fields=fields,
                    field_attr=field_attr,
                    data_attr=data_attr,
                    table_field=table_field,
                    col_type_override=col_type_override,
                    index=index,
                    totals=totals,
                    expression=expression,
                )
        elif field == 'rb_subtraction':
            values = self.decode_mathematical_columns(data_attr=data_attr)
            if values is not None:
                expression = ExpressionWrapper(NullIf(F(values[0]), 0) - F(values[1]), output_field=FloatField())
                self.get_mathematical_field(
                    fields=fields,
                    field_attr=field_attr,
                    data_attr=data_attr,
                    table_field=table_field,
                    col_type_override=col_type_override,
                    index=index,
                    totals=totals,
                    expression=expression,
                )

    @staticmethod
    def decode_mathematical_columns(
        data_attr,
        first_value_column_name='first_value_column',
        second_value_column_name='second_value_column',
    ):
        first_value_column = data_attr.get(first_value_column_name)
        second_value_column = data_attr.get(second_value_column_name)
        if not first_value_column or not second_value_column:
            return None

        first_value_column = decode_attribute(first_value_column)
        second_value_column = decode_attribute(second_value_column)

        return first_value_column, second_value_column

    def get_mathematical_percentage_field(self, fields, field_attr, data_attr, table_field, index, totals):
        values = self.decode_mathematical_columns(
            data_attr=data_attr,
            first_value_column_name='numerator_column',
            second_value_column_name='denominator_column',
        )
        if values is None:
            return False

        expression = ExpressionWrapper(NullIf(F(values[0]) * 100.00, 0) / F(values[1]), output_field=FloatField())
        decimal_places = data_attr.get('decimal_places', 2)
        field_attr['decimal_places'] = int(decimal_places)
        alignment_class = ALIGNMENT_CLASS.get(int(data_attr.get('alignment', ALIGNMENT_CHOICE_RIGHT)))
        field_attr['options'] = {}
        field = table_field['field']

        column_id = data_attr.get('column_id')
        field_name = decode_attribute(column_id) if column_id else f'{field}_{index}'
        field_attr['annotations'] = {field_name: expression}

        field_attr.update(
            {
                'field': field_name,
                'column_name': field_name,
                'model_path': '',
                'render': [render_replace(html='%1%&thinsp;%', column=field_name)],
                'hidden': data_attr.get('hidden', 0) == '1',
            }
        )
        if alignment_class != '':
            field_attr['column_defs'] = {'className': alignment_class}
        field = self.number_field(**field_attr)

        if totals is not None:
            show_total = data_attr.get('show_totals')
            if show_total == '1':
                self.set_percentage_total(
                    totals=totals,
                    field_name=field_name,
                    denominator=values[1],
                    numerator=values[0],
                    decimal_places=decimal_places,
                    css_class=alignment_class,
                )
        fields.append(field)

    def get_mathematical_field(
        self,
        fields,
        field_attr,
        data_attr,
        table_field,
        col_type_override,
        index,
        totals,
        expression,
    ):
        decimal_places = data_attr.get('decimal_places', 2)
        alignment_class = ALIGNMENT_CLASS.get(int(data_attr.get('alignment', ALIGNMENT_CHOICE_RIGHT)))
        field_attr['decimal_places'] = int(decimal_places)
        field_attr['options'] = {}
        field = table_field['field']
        column_id = data_attr.get('column_id')
        field_name = decode_attribute(column_id) if column_id else f'{field}_{index}'
        field_attr['annotations'] = {field_name: expression}

        field_attr.update(
            {
                'field': field_name,
                'column_name': field_name,
                'model_path': '',
                'trim_zeros': False,
                'hidden': data_attr.get('hidden', 0) == '1',
                'css_class': alignment_class,
            }
        )
        if alignment_class != '':
            field_attr['column_defs'] = {'className': alignment_class}
        field = self.number_field(**field_attr)

        if totals is not None:
            show_total = data_attr.get('show_totals')
            if show_total == '1':
                self.set_number_total(
                    totals=totals,
                    field_name=field_name,
                    col_type_override=col_type_override,
                    decimal_places=decimal_places,
                    css_class=alignment_class,
                )
        fields.append(field)

    def get_reverse_foreign_key_str_field(self, col_type_override, data_attr, field_attr, index):
        col_type_override.table = None
        field_name = f'{col_type_override.field_name}_{index}'
        field = copy.deepcopy(col_type_override)
        delimiter_type = int(data_attr.get('delimiter_type', REVERSE_FOREIGN_KEY_DELIMITER_COMMA))

        sub_query = None
        if int(data_attr.get('has_filter', 0)) == 1:
            _filter = json.loads(decode_attribute(data_attr['filter']))
            prefix_field_name = col_type_override.field_name.split('__')[0]
            sub_query = self.process_filters(search_filter_data=_filter, prefix_field_name=prefix_field_name)
        field.setup_annotations(delimiter_type=delimiter_type, sub_filter=sub_query, field_name=field_name)
        if field_attr:
            field = (field, field_attr)
        return field

    def get_reverse_foreign_key_bool_field(self, col_type_override, data_attr, field_attr, index):
        col_type_override.table = None
        field_name = f'{col_type_override.field_name}_{index}'
        field = copy.deepcopy(col_type_override)
        sub_query = None
        if int(data_attr.get('has_filter', 0)) == 1:
            _filter = json.loads(decode_attribute(data_attr['filter']))
            prefix_field_name = col_type_override.field_name.split('__')[0]
            sub_query = self.process_filters(search_filter_data=_filter, prefix_field_name=prefix_field_name)
        annotations_type = int(data_attr.get('annotations_type', REVERSE_FOREIGN_KEY_ANNOTATION_BOOLEAN_XOR))
        field.setup_annotations(
            annotations_type=annotations_type,
            sub_filter=sub_query,
            field_name=field_name,
        )
        if field_attr:
            field = (field, field_attr)
        return field

    def get_reverse_foreign_key_choice_field(self, col_type_override, data_attr, field_attr, index):
        col_type_override.table = None
        field_name = f'{col_type_override.field_name}_{index}'
        field = copy.deepcopy(col_type_override)
        sub_query = None
        delimiter_type = int(data_attr.get('delimiter_type', REVERSE_FOREIGN_KEY_DELIMITER_COMMA))
        if int(data_attr.get('has_filter', 0)) == 1:
            _filter = json.loads(decode_attribute(data_attr['filter']))
            prefix_field_name = col_type_override.field_name.split('__')[0]
            sub_query = self.process_filters(search_filter_data=_filter, prefix_field_name=prefix_field_name)
        field.setup_annotations(delimiter_type=delimiter_type, sub_filter=sub_query, field_name=field_name)
        if field_attr:
            field = (field, field_attr)
        return field

    def get_reverse_foreign_key_date_field(self, col_type_override, data_attr, field_attr, index):
        col_type_override.table = None
        field_name = f'{col_type_override.field_name}_{index}'
        field = copy.deepcopy(col_type_override)
        sub_query = None
        delimiter_type = int(data_attr.get('delimiter_type', REVERSE_FOREIGN_KEY_DELIMITER_COMMA))
        date_format_type = int(data_attr.get('date_format', DATE_FORMAT_TYPE_DD_MM_YY_SLASH))
        annotations_type = int(data_attr.get('annotations_type', REVERSE_FOREIGN_KEY_ANNOTATION_BOOLEAN_XOR))

        if int(data_attr.get('has_filter', 0)) == 1:
            _filter = json.loads(decode_attribute(data_attr['filter']))
            prefix_field_name = col_type_override.field_name.split('__')[0]
            sub_query = self.process_filters(search_filter_data=_filter, prefix_field_name=prefix_field_name)

        field.setup_annotations(
            delimiter_type=delimiter_type,
            date_format_type=date_format_type,
            annotations_type=annotations_type,
            sub_filter=sub_query,
            field_name=field_name,
        )
        if field_attr:
            field = (field, field_attr)
        return field


class DescriptionColumn(ColumnBase):
    def row_result(self, data, _page_data, columns):
        html = self.options['html']

        for column in columns:
            if not isinstance(column, DescriptionColumn):
                data[column.column_name] = column.row_result(data, _page_data)

        try:
            template = Template(html)
            context = Context(data)
            return template.render(context)
        except TemplateSyntaxError as e:
            return f'Error in description ({e})'
