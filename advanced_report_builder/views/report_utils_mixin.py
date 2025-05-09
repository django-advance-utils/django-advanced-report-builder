import copy
import json
import operator
from functools import reduce

from django.db.models import ExpressionWrapper, FloatField
from django.db.models.functions import NullIf
from django_datatables.columns import CurrencyColumn, CurrencyPenceColumn

from advanced_report_builder.columns import (
    ReportBuilderCurrencyColumn,
    ReportBuilderCurrencyPenceColumn,
    ReportBuilderNumberColumn,
)
from advanced_report_builder.exceptions import ReportError
from advanced_report_builder.field_utils import ReportBuilderFieldUtils
from advanced_report_builder.filter_query import FilterQueryMixin
from advanced_report_builder.globals import (
    ALIGNMENT_CHOICE_RIGHT,
    ALIGNMENT_CLASS,
    ANNOTATION_CHOICE_COUNT,
    ANNOTATION_CHOICE_NA,
    ANNOTATION_FUNCTIONS,
)
from advanced_report_builder.utils import decode_attribute


class ReportUtilsMixin(ReportBuilderFieldUtils, FilterQueryMixin):
    use_annotations = True
    number_field = ReportBuilderNumberColumn

    def get_number_field(
        self,
        annotations_type,
        append_annotation_query,
        index,
        table_field,
        data_attr,
        fields,
        col_type_override,
        extra_filter=None,
        title_suffix='',
        multiple_index=0,
        decimal_places=None,
        convert_currency_fields=False,
        totals=None,
        divider=None,
        additional_options=None,
    ):
        field_name = table_field['field']
        alignment_class = ALIGNMENT_CLASS.get(int(data_attr.get('alignment', ALIGNMENT_CHOICE_RIGHT)))
        new_field_name = field_name
        css_class = None
        annotation_filter = None
        if annotations_type != ANNOTATION_CHOICE_NA or append_annotation_query:
            b64_filter = data_attr.get('filter')
            if b64_filter:
                _filter = decode_attribute(b64_filter)
                _filter = json.loads(_filter)
                annotation_filter = self.process_filters(search_filter_data=_filter, extra_filter=extra_filter)
            elif extra_filter:
                annotation_filter = reduce(operator.and_, [extra_filter])

        if int(data_attr.get('display_heading', 1)) == 0:
            title = ''
        elif int(data_attr.get('append_column_title', 0)) == 0:
            title = title_suffix
        else:
            title = title_suffix + ' ' + table_field.get('title')
        if col_type_override:
            col_type_override.table = None
            field = copy.deepcopy(col_type_override)
            if field.model_path and isinstance(field.field, str) and field.field.startswith(field.model_path):
                raw_field_name = field.field[len(field.model_path) :]
            else:
                raw_field_name = field.field

            if convert_currency_fields:
                if isinstance(field, CurrencyPenceColumn):
                    field.__class__ = ReportBuilderCurrencyPenceColumn
                elif isinstance(field, CurrencyColumn):
                    field.__class__ = ReportBuilderCurrencyColumn

            if append_annotation_query and field.annotations:
                css_class = field.column_defs.get('className')
                if css_class is None:
                    css_class = alignment_class
                else:
                    css_class += ' ' + alignment_class
                field.column_defs['className'] = css_class
                if title:
                    field.title = title

                field = copy.deepcopy(field)

                current_annotations = getattr(field.annotations[field_name], 'filter', None)
                # assert False, field.annotations[field_name]
                if current_annotations is None:
                    raise ReportError(f'Sorry unable to annotate {field_name}. The query is to complex to modify.')
                    # field.annotations[field_name].expression is where the query is!
                elif annotation_filter is not None and len(annotation_filter) > 0:
                    new_annotations = current_annotations & annotation_filter
                    field.annotations[field_name].filter = new_annotations
                new_field_name = f'{field_name}_{index}'
                field.annotations[new_field_name] = field.annotations.pop(field_name)
                field.field = new_field_name
                field_name = new_field_name

            if annotations_type == ANNOTATION_CHOICE_COUNT:
                new_field_name = self.get_new_annotation_field_name(
                    annotations_type=annotations_type,
                    field_name=field_name,
                    index=index,
                    data_attr=data_attr,
                )
                number_function_kwargs = {}
                if title:
                    number_function_kwargs['title'] = title
                if alignment_class != '':
                    css_class = alignment_class
                    number_function_kwargs['column_defs'] = {'className': css_class}
                function_type = ANNOTATION_FUNCTIONS[annotations_type]
                number_function_kwargs['options'] = {}
                self.set_extra_number_field_kwargs(
                    data_attr=data_attr,
                    options=number_function_kwargs['options'],
                    multiple_index=multiple_index,
                    additional_options=additional_options,
                )
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

                number_function_kwargs.update({'field': new_field_name, 'column_name': new_field_name})
                field = self.number_field(**number_function_kwargs)
            else:
                css_class = field.column_defs.get('className')
                if css_class is None:
                    css_class = alignment_class
                else:
                    css_class += ' ' + alignment_class
                field.column_defs['className'] = css_class
                if title:
                    field.title = title
                if field.annotations:
                    if not self.use_annotations:
                        field.options['calculated'] = True
                        field.aggregations = col_type_override.annotations
                        field.annotations = []
                    if title:
                        field.title = title

                    self.set_extra_number_field_kwargs(
                        data_attr=data_attr,
                        options=field.options,
                        multiple_index=multiple_index,
                        additional_options=additional_options,
                    )
                elif annotations_type != ANNOTATION_CHOICE_NA:
                    new_field_name = self.get_new_annotation_field_name(
                        annotations_type=annotations_type,
                        field_name=field_name,
                        index=index,
                        data_attr=data_attr,
                    )
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
                    self.set_extra_number_field_kwargs(
                        data_attr=data_attr,
                        options=field.options,
                        multiple_index=multiple_index,
                        additional_options=additional_options,
                    )
            fields.append(field)
        else:
            number_function_kwargs = {'title': title}
            decimal_places = data_attr.get('decimal_places', decimal_places)
            if decimal_places:
                number_function_kwargs['decimal_places'] = int(decimal_places)
            if annotations_type:
                number_function_kwargs['options'] = {}
                self.set_extra_number_field_kwargs(
                    data_attr=data_attr,
                    options=number_function_kwargs['options'],
                    multiple_index=multiple_index,
                    additional_options=additional_options,
                )

                new_field_name = self.get_new_annotation_field_name(
                    annotations_type=annotations_type,
                    field_name=field_name,
                    index=index,
                    data_attr=data_attr,
                )
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
            number_function_kwargs.update({'field': field_name, 'column_name': field_name, 'model_path': ''})
            field = self.number_field(**number_function_kwargs)
            fields.append(field)

        if totals is not None:
            show_total = data_attr.get('show_totals')
            if show_total == '1':
                self.set_number_total(
                    totals=totals,
                    field_name=new_field_name,
                    col_type_override=col_type_override,
                    decimal_places=decimal_places,
                    css_class=css_class,
                )
        return field_name

    @staticmethod
    def get_new_annotation_field_name(annotations_type, field_name, index, data_attr):
        annotation_column_id = data_attr.get('annotation_column_id')
        if annotation_column_id:
            return decode_attribute(annotation_column_id)
        return f'{annotations_type}_{field_name}_{index}'

    def set_extra_number_field_kwargs(self, data_attr, options, multiple_index, additional_options):
        pass

    # noinspection PyUnusedLocal,PyMethodMayBeStatic
    def set_number_total(self, totals, field_name, col_type_override, decimal_places, css_class=''):
        totals[field_name] = {
            'sum': 'to_fixed',
            'decimal_places': decimal_places,
            'css_class': css_class,
        }

    def set_annotation_total(self, totals, field_name, col_type_override, decimal_places, css_class=''):
        return self.set_number_total(totals, field_name, col_type_override, decimal_places, css_class)

    def set_percentage_total(self, totals, field_name, denominator, numerator, decimal_places, css_class=''):
        totals[field_name] = {
            'sum': 'percentage',
            'decimal_places': decimal_places,
            'denominator': denominator,
            'numerator': numerator,
            'css_class': css_class,
        }
