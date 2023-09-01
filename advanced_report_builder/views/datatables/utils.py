import copy

from django.db.models import Q
from django_datatables.plugins.column_totals import ColumnTotals

from advanced_report_builder.columns import ReportBuilderDateColumn
from advanced_report_builder.globals import DATE_FIELDS, NUMBER_FIELDS, CURRENCY_COLUMNS, LINK_COLUMNS
from advanced_report_builder.globals import DATE_FORMAT_TYPES_DJANGO_FORMAT, ANNOTATION_VALUE_FUNCTIONS
from advanced_report_builder.utils import split_attr, decode_attribute
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
            date_function_kwargs = {'title': title,
                                    'date_format': date_format}

            if annotations_value != 0:
                new_field_name = f'{annotations_value}_{field_name}_{index}'
                function = ANNOTATION_VALUE_FUNCTIONS[annotations_value]
                date_function_kwargs['annotations_value'] = {new_field_name: function(field_name)}
                field_name = new_field_name

            date_function_kwargs.update({'field': field_name,
                                         'column_name': field_name})

            field = self.date_field(**date_function_kwargs)
            fields.append(field)

        return field_name

    @staticmethod
    def get_link_field(table_field, fields, col_type_override):
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

    def process_query_results(self, report_builder_class, table, base_model,
                              fields_used, table_fields, pivot_fields=None):
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

            fields_used.add(field)
            django_field, col_type_override, _, _ = self.get_field_details(base_model=base_model,
                                                                           field=field,
                                                                           table=table,
                                                                           report_builder_class=report_builder_class,
                                                                           field_attr=field_attr)

            data_attr = split_attr(table_field)
            if int(data_attr.get('display_heading', 1)) == 0:
                field_attr['title'] = ''

            if isinstance(django_field, DATE_FIELDS):
                field_name = self.get_date_field(index=index,
                                                 col_type_override=col_type_override,
                                                 table_field=table_field,
                                                 fields=fields)
            elif isinstance(django_field, NUMBER_FIELDS) and (django_field is None or django_field.choices is None):
                annotations_type = int(data_attr.get('annotations_type', 0))
                if annotations_type != 0:
                    has_annotations = True
                decimal_places = data_attr.get('decimal_places')

                if annotations_type != 0 and data_attr.get('multiple_columns') == '1':
                    query = self.extra_filters(query=table.model.objects)
                    multiple_column_field = data_attr.get('multiple_column_field')

                    field_report_builder_class = self._get_report_builder_class(
                        base_model=base_model,
                        field_str=multiple_column_field,
                        report_builder_class=report_builder_class)
                    _fields = field_report_builder_class.default_multiple_column_fields
                    default_multiple_column_fields = [multiple_column_field + '__' + x for x in _fields]
                    order_by = f'{multiple_column_field}__{field_report_builder_class.default_multiple_pk}'

                    results = query.order_by(order_by).\
                        distinct(multiple_column_field).values(multiple_column_field, *default_multiple_column_fields)

                    for multiple_index, result in enumerate(results):
                        suffix = self._set_multiple_title(database_values=result,
                                                          value_prefix=multiple_column_field,
                                                          fields=_fields,
                                                          text=field_report_builder_class.default_multiple_column_text)
                        extra_filter = Q((multiple_column_field, result[multiple_column_field]))

                        field_name = self.get_number_field(annotations_type=annotations_type,
                                                           index=f'{index}_{multiple_index}',
                                                           data_attr=data_attr,
                                                           table_field=table_field,
                                                           fields=fields,
                                                           totals=totals,
                                                           col_type_override=col_type_override,
                                                           extra_filter=extra_filter,
                                                           title_suffix=suffix,
                                                           decimal_places=decimal_places)
                else:
                    field_name = self.get_number_field(annotations_type=annotations_type,
                                                       index=index,
                                                       data_attr=data_attr,
                                                       table_field=table_field,
                                                       fields=fields,
                                                       totals=totals,
                                                       col_type_override=col_type_override,
                                                       decimal_places=decimal_places)

            elif isinstance(col_type_override, LINK_COLUMNS):
                self.get_link_field(table_field=table_field,
                                    col_type_override=col_type_override,
                                    fields=fields)
            else:
                if col_type_override is not None:
                    if data_attr.get('annotation_label') == '1':
                        if isinstance(col_type_override.field, list):
                            table.initial_values += col_type_override.field
                        else:
                            table.initial_values.append(col_type_override.field)

                field_name = field
                if isinstance(col_type_override, CURRENCY_COLUMNS) and totals is not None:

                    css_class = col_type_override.column_defs.get('className')
                    show_total = data_attr.get('show_totals')
                    if show_total == '1':
                        totals[field_name] = {'sum': 'to_fixed', 'decimal_places': 2,
                                              'css_class': css_class}
                if field_attr:
                    field = (field, field_attr)
                fields.append(field)
            if not first_field_name:
                first_field_name = field_name

        if not has_annotations and len(report_builder_class.default_columns) > 0:
            table.add_columns(*report_builder_class.default_columns)
        table.add_columns(*fields)
        table.show_pivot_table = False
        if pivot_fields is not None:
            for pivot_field in pivot_fields:
                pivot_field_data = self._get_pivot_details(base_model=base_model,
                                                           pivot_str=pivot_field['field'],
                                                           report_builder_class=report_builder_class)
                if pivot_field_data is None:
                    continue

                if pivot_field_data['id'] not in fields_used:
                    table.add_columns('.' + pivot_field_data['id'])
                    fields_used.add(pivot_field_data['id'])

                pivot_field_details = pivot_field_data['details']
                table.add_js_filters(pivot_field_details['type'],
                                     pivot_field_data['id'],
                                     filter_title=pivot_field_details['title'],
                                     **pivot_field_details['kwargs'])
                table.show_pivot_table = True

        if totals:
            totals[first_field_name] = {'text': 'Totals'}
            table.add_plugin(self.column_totals_class, totals)

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
            query = self.process_query_filters(query=query,
                                               search_filter_data=report_query.query)
        return query
