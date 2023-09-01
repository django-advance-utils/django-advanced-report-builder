import copy
import json
import operator
from functools import reduce

from django.db.models import FloatField, ExpressionWrapper
from django.db.models.functions import NullIf
from django_datatables.columns import CurrencyPenceColumn, CurrencyColumn

from advanced_report_builder.columns import ReportBuilderCurrencyPenceColumn, ReportBuilderCurrencyColumn, \
    ReportBuilderNumberColumn
from advanced_report_builder.field_utils import ReportBuilderFieldUtils
from advanced_report_builder.filter_query import FilterQueryMixin
from advanced_report_builder.globals import ANNOTATION_FUNCTIONS, ANNOTATION_CHOICE_COUNT
from advanced_report_builder.utils import decode_attribute


class ReportUtilsMixin(ReportBuilderFieldUtils, FilterQueryMixin):
    use_annotations = True
    number_field = ReportBuilderNumberColumn

    def get_number_field(self, annotations_type, index, table_field, data_attr, fields, col_type_override,
                         extra_filter=None, title_suffix='', multiple_index=0, decimal_places=None,
                         convert_currency_fields=False, totals=None, divider=None):
        field_name = table_field['field']
        css_class = None
        annotation_filter = None
        if annotations_type != 0:
            b64_filter = data_attr.get('filter')
            if b64_filter:
                _filter = decode_attribute(b64_filter)
                _filter = json.loads(_filter)
                annotation_filter = self.process_filters(search_filter_data=_filter, extra_filter=extra_filter)
            elif extra_filter:
                annotation_filter = reduce(operator.and_, [extra_filter])

        if int(data_attr.get('display_heading', 1)) == 0:
            title = ''
        else:
            title = title_suffix + ' ' + table_field.get('title')
        if col_type_override:
            col_type_override.table = None
            field = copy.deepcopy(col_type_override)
            if field.model_path and isinstance(field.field, str) and field.field.startswith(field.model_path):
                raw_field_name = field.field[len(field.model_path):]
            else:
                raw_field_name = field.field

            if convert_currency_fields:
                if isinstance(field, CurrencyPenceColumn):
                    field.__class__ = ReportBuilderCurrencyPenceColumn
                elif isinstance(field, CurrencyColumn):
                    field.__class__ = ReportBuilderCurrencyColumn

            if field.annotations:
                if not self.use_annotations:
                    field.options['calculated'] = True
                    field.aggregations = col_type_override.annotations
                    field.annotations = []
                if title:
                    field.title = title
                self.set_extra_number_field_kwargs(data_attr=data_attr,
                                                   options=field.options,
                                                   multiple_index=multiple_index)

            elif annotations_type == ANNOTATION_CHOICE_COUNT:
                new_field_name = f'{annotations_type}_{field_name}_{index}'
                number_function_kwargs = {}
                if title:
                    number_function_kwargs['title'] = title
                function_type = ANNOTATION_FUNCTIONS[annotations_type]

                number_function_kwargs['options'] = {}
                self.set_extra_number_field_kwargs(data_attr=data_attr,
                                                   options=number_function_kwargs['options'],
                                                   multiple_index=multiple_index)
                if annotation_filter:
                    function = function_type(raw_field_name, filter=annotation_filter)
                else:
                    function = function_type(raw_field_name)
                if divider:
                    function = ExpressionWrapper(function / NullIf(divider, 0), output_field=FloatField())
                if self.use_annotations:
                    number_function_kwargs['annotations'] = {new_field_name: function}
                else:
                    number_function_kwargs['options']['calculated'] = True
                    number_function_kwargs['aggregations'] = {new_field_name: function}
                    number_function_kwargs['annotations'] = []

                number_function_kwargs.update({'field': new_field_name,
                                               'column_name': field_name})
                field = self.number_field(**number_function_kwargs)
            else:
                css_class = field.column_defs.get('className')
                if title:
                    field.title = title
                if annotations_type != 0:
                    new_field_name = f'{annotations_type}_{field_name}_{index}'
                    function_type = ANNOTATION_FUNCTIONS[annotations_type]
                    if annotation_filter:
                        function = function_type(raw_field_name, filter=annotation_filter)
                    else:
                        function = function_type(raw_field_name)
                    if divider:
                        function = ExpressionWrapper(function / NullIf(divider, 0), output_field=FloatField())
                    if self.use_annotations:
                        field.annotations = {new_field_name: function}
                    else:
                        field.options['calculated'] = True
                        field.aggregations = {new_field_name: function}
                        field.annotations = []

                    field.field = new_field_name
                    self.set_extra_number_field_kwargs(data_attr=data_attr,
                                                       options=field.options,
                                                       multiple_index=multiple_index)
            fields.append(field)
        else:
            number_function_kwargs = {'title': title}
            decimal_places = data_attr.get('decimal_places', decimal_places)
            if decimal_places:
                number_function_kwargs['decimal_places'] = int(decimal_places)
            if annotations_type:
                number_function_kwargs['options'] = {}
                self.set_extra_number_field_kwargs(data_attr=data_attr,
                                                   options=number_function_kwargs['options'],
                                                   multiple_index=multiple_index)
                new_field_name = f'{annotations_type}_{field_name}_{index}'
                function_type = ANNOTATION_FUNCTIONS[annotations_type]
                if annotation_filter:
                    function = function_type(field_name, filter=annotation_filter)
                else:
                    function = function_type(field_name)

                if self.use_annotations:
                    number_function_kwargs['annotations'] = {new_field_name: function}
                else:
                    number_function_kwargs['options']['calculated'] = True
                    number_function_kwargs['aggregations'] = {new_field_name: function}
                    number_function_kwargs['annotations'] = []
                field_name = new_field_name
            number_function_kwargs.update({'field': field_name,
                                           'column_name': field_name,
                                           'model_path': ''})
            field = self.number_field(**number_function_kwargs)
            fields.append(field)

        if totals is not None:
            show_total = data_attr.get('show_totals')
            if show_total == '1':
                self.set_number_total(totals=totals,
                                      field_name=field_name,
                                      col_type_override=col_type_override,
                                      decimal_places=decimal_places,
                                      css_class=css_class)

        return field_name

    def set_extra_number_field_kwargs(self, data_attr, options, multiple_index):
        pass

    # noinspection PyUnusedLocal,PyMethodMayBeStatic
    def set_number_total(self, totals, field_name, col_type_override, decimal_places, css_class):
        totals[field_name] = {'sum': 'to_fixed', 'decimal_places': decimal_places, 'css_class': css_class}
