from django.contrib.humanize.templatetags.humanize import intcomma
from django.contrib.postgres.aggregates import ArrayAgg, BoolAnd, BoolOr, StringAgg
from django.db.models import BooleanField, Count, Max, Min
from django.db.models.functions import Cast
from django_datatables.columns import (
    ColumnBase,
    ColumnLink,
    CurrencyColumn,
    CurrencyPenceColumn,
    ManyToManyColumn,
    NoHeadingColumn,
)
from django_datatables.helpers import DUMMY_ID, get_url, render_replace
from django_datatables.model_def import DatatableModel

from advanced_report_builder.globals import (
    DATE_FORMAT_TYPE_DD_MM_YY_SLASH,
    DATE_FORMAT_TYPES_DJANGO_FORMAT,
    REVERSE_FOREIGN_KEY_ANNOTATION_BOOLEAN_AND,
    REVERSE_FOREIGN_KEY_ANNOTATION_BOOLEAN_ARRAY,
    REVERSE_FOREIGN_KEY_ANNOTATION_BOOLEAN_XOR,
    REVERSE_FOREIGN_KEY_ANNOTATION_DATE_ARRAY,
    REVERSE_FOREIGN_KEY_ANNOTATION_DATE_MAX,
    REVERSE_FOREIGN_KEY_ANNOTATION_DATE_MIN,
    REVERSE_FOREIGN_KEY_DELIMITER_COMMA,
    REVERSE_FOREIGN_KEY_DELIMITER_VALUES,
)


class ReportBuilderDateColumn(ColumnBase):
    def __init__(self, *, date_format=None, **kwargs):
        if not self.initialise(locals()):
            return
        super().__init__(**kwargs)
        if date_format:
            self.date_format = date_format
        else:
            self.date_format = '%d/%m/%Y'

    def row_result(self, data, _page_data):
        try:
            date = data[self.field].strftime(self.date_format)
            return date
        except AttributeError:
            return ''


class ReportBuilderNumberColumn(ColumnBase):
    def __init__(self, *, decimal_places=0, trim_zeros=True, **kwargs):
        if not self.initialise(locals()):
            return
        super().__init__(**kwargs)
        self.decimal_places = f'{{:.{decimal_places}f}}'
        self.trim_zeros = trim_zeros

    def row_result(self, data, _page_data):
        number = data.get(self.field)
        if number is None:
            return ''
        else:
            number = self.decimal_places.format(number)
        if self.trim_zeros and '.' in number:
            return number.rstrip('0').rstrip('.')
        else:
            return number


class ReportBuilderCurrencyPenceColumn(CurrencyPenceColumn):
    def row_result(self, data, _page_data):
        try:
            return intcomma(f'{data[self.field] / 100.0:.2f}')
        except (KeyError, TypeError):
            return '0.00'


class ReportBuilderCurrencyColumn(CurrencyColumn):
    def row_result(self, data, _page_data):
        try:
            return intcomma(f'{data[self.field]:.2f}')
        except (KeyError, TypeError):
            return '0.00'


class ArrowColumn(NoHeadingColumn):
    def __init__(self, **kwargs):
        if not self.initialise(locals()):
            return
        kwargs['render'] = [{'html': '<i class="fa fa-angle-right fa-2x"></i>', 'function': 'Html'}]
        kwargs['width'] = '10px'
        super().__init__(**kwargs)


class ColourColumn(ColumnBase):
    def __init__(self, **kwargs):
        if not self.initialise(locals()):
            return
        kwargs['render'] = [
            render_replace(
                html='<span style="display: inline-block; width: 60px; height: 15px;'
                ' background-color: #%1%; vertical-align: middle;"></span>',
                column=kwargs['column_name'],
            )
        ]
        super().__init__(**kwargs)


class FilterForeignKeyColumn(ColumnBase):
    def get_query_options(self):
        values = self.model.objects.distinct(self.field).order_by(self.field).values_list(self.field, flat=True)
        return {v: v for v in values if v}


class ReverseForeignKeyStrColumn(ColumnBase):
    def __init__(self, field_name, report_builder_class_name, **kwargs):
        if not self.initialise(locals()):
            return
        super().__init__(**kwargs)
        self.field_name = field_name
        self.report_builder_class_name = report_builder_class_name

    def setup_annotations(self, delimiter_type=None, sub_filter=None, field_name=None):
        if field_name is None:
            field_name = self.field_name
        delimiter = REVERSE_FOREIGN_KEY_DELIMITER_VALUES[delimiter_type]

        self.annotations = {
            field_name: StringAgg(self.field_name, delimiter=delimiter, distinct=True, filter=sub_filter)
        }


class ReverseForeignKeyBoolColumn(ColumnBase):
    def __init__(self, field_name, report_builder_class_name, **kwargs):
        if not self.initialise(locals()):
            return
        super().__init__(**kwargs)
        self.field_name = field_name
        self.report_builder_class_name = report_builder_class_name

    def setup_annotations(self, annotations_type, sub_filter=None, field_name=None):
        if field_name is None:
            field_name = self.field_name

        if annotations_type == REVERSE_FOREIGN_KEY_ANNOTATION_BOOLEAN_XOR:
            self.annotations = {field_name: BoolOr(Cast(self.field_name, BooleanField()), filter=sub_filter)}
        elif annotations_type == REVERSE_FOREIGN_KEY_ANNOTATION_BOOLEAN_AND:
            self.annotations = {field_name: BoolAnd(Cast(self.field_name, BooleanField()), filter=sub_filter)}
        elif annotations_type == REVERSE_FOREIGN_KEY_ANNOTATION_BOOLEAN_ARRAY:
            self.annotations = {field_name: ArrayAgg(self.field_name, distinct=True, filter=sub_filter)}


class ReverseForeignKeyChoiceColumn(ColumnBase):
    def __init__(self, field_name, report_builder_class_name, **kwargs):
        if not self.initialise(locals()):
            return
        self.field_name = field_name
        self.choices = None
        self.report_builder_class_name = report_builder_class_name
        self.delimiter_type = REVERSE_FOREIGN_KEY_DELIMITER_COMMA
        super().__init__(**kwargs)

    def setup_results(self, request, all_results):
        _, django_field, _ = DatatableModel.get_setup_data(self.model, self.field_name)
        self.choices = {c[0]: c[1] for c in django_field.choices}

    def row_result(self, data, _page_data):
        results = []
        for x in data.get(self.field):
            results.append(self.choices.get(x, ''))
        delimiter = REVERSE_FOREIGN_KEY_DELIMITER_VALUES[self.delimiter_type]
        return delimiter.join(results)

    def setup_annotations(self, delimiter_type=None, sub_filter=None, field_name=None):
        if field_name is None:
            field_name = self.field_name
        self.delimiter_type = delimiter_type
        self.annotations = {field_name: ArrayAgg(self.field_name, distinct=True, filter=sub_filter)}


class ReverseForeignKeyDateColumn(ColumnBase):
    def __init__(self, field_name, report_builder_class_name, **kwargs):
        if not self.initialise(locals()):
            return
        super().__init__(**kwargs)
        self.field_name = field_name
        self.report_builder_class_name = report_builder_class_name
        self.delimiter_type = REVERSE_FOREIGN_KEY_DELIMITER_COMMA
        self.date_format_type = DATE_FORMAT_TYPE_DD_MM_YY_SLASH
        self.annotations_type = REVERSE_FOREIGN_KEY_ANNOTATION_DATE_ARRAY

    def setup_annotations(
        self,
        delimiter_type=None,
        date_format_type=None,
        annotations_type=None,
        sub_filter=None,
        field_name=None,
    ):
        if field_name is None:
            field_name = self.field_name
        self.delimiter_type = delimiter_type
        self.date_format_type = date_format_type
        self.annotations_type = annotations_type

        if annotations_type == REVERSE_FOREIGN_KEY_ANNOTATION_DATE_ARRAY:
            self.annotations = {field_name: ArrayAgg(self.field_name, distinct=True, filter=sub_filter)}
        elif annotations_type == REVERSE_FOREIGN_KEY_ANNOTATION_DATE_MIN:
            self.annotations = {field_name: Min(self.field_name, sub_filter=sub_filter)}

        elif annotations_type == REVERSE_FOREIGN_KEY_ANNOTATION_DATE_MAX:
            self.annotations = {field_name: Max(self.field_name, sub_filter=sub_filter)}

    def row_result(self, data, _page_data):
        field = self.field
        if isinstance(field, list):
            field = field[-1]
        try:
            date_formate_type_str = DATE_FORMAT_TYPES_DJANGO_FORMAT[self.date_format_type]
            results = []
            date_values = data[field]
            if date_values is None:
                return ''
            if isinstance(date_values, list):
                for value in date_values:
                    results.append(value.strftime(date_formate_type_str))
                delimiter = REVERSE_FOREIGN_KEY_DELIMITER_VALUES[self.delimiter_type]
                return delimiter.join(results)
            else:
                return date_values.strftime(date_formate_type_str)
        except AttributeError:
            return ''


class ReportBuilderColumnLink(ColumnLink):
    """Sometimes you may want to have a report where the links don't work.
    This is used for when you have a wall board"""

    @property
    def url(self):
        return self._url

    def setup_link(self, link_css, link_html):
        if self.enable_links():
            link_css = f' class="{link_css}"' if link_css else ''
            link = f'<a{link_css} href="{self.url}">{{}}</a>'
        else:
            link = '{}'
        if isinstance(self.field, list | tuple):
            self.options['render'] = [
                render_replace(column=self.column_name + ':0', html=link.format(link_html), var='999999'),
                render_replace(column=self.column_name + ':1'),
            ]
        elif self.var not in link_html:
            self.options['render'] = [
                render_replace(column=self.link_ref_column, html=link.format(link_html), var='999999')
            ]
        else:
            self.options['render'] = [
                render_replace(column=self.column_name, html=link.format(link_html), var=self.var),
                render_replace(column=self.link_ref_column, var='999999'),
            ]

    @url.setter
    def url(self, url_name):
        if self.enable_links():
            self._url = get_url(url_name)
        else:
            self._url = f'#?{DUMMY_ID}'

    def enable_links(self):
        return (
            not self.table
            or self.table.view is None
            or self.table.view.kwargs.get('enable_links')
            or getattr(self.table.view, 'enable_links', False)
        )


class RecordCountColumn(ColumnBase):
    def __init__(self, field=None, **kwargs):
        if 'annotations' not in kwargs:
            kwargs['annotations'] = {'record_count': Count(1)}
        if 'column_name' not in kwargs:
            kwargs['column_name'] = 'record_count'
        super().__init__(field, **kwargs)


class ReportBuilderManyToManyColumn(ManyToManyColumn):
    def __init__(self, *arg, **kwargs):
        if not self.initialise(locals()):
            return
        super().__init__(*arg, **kwargs)
        if self.model_path is not None:
            self.field = 'id'

    def row_result(self, data_dict, page_results):
        return page_results['m2m' + self.column_name].get(data_dict[self.model_path + 'id'], self.blank)
