from django.contrib.humanize.templatetags.humanize import intcomma
from django.contrib.postgres.aggregates import StringAgg, BoolOr, BoolAnd, ArrayAgg
from django.db.models import Count, BooleanField
from django.db.models.functions import Cast
from django_datatables.columns import ColumnBase, CurrencyPenceColumn, CurrencyColumn, NoHeadingColumn, ColumnLink, \
    ManyToManyColumn
from django_datatables.helpers import get_url, DUMMY_ID, render_replace


class ReportBuilderDateColumn(ColumnBase):

    def __init__(self, *,  date_format=None, **kwargs):
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
            return ""


class ReportBuilderNumberColumn(ColumnBase):

    def __init__(self, *,  decimal_places=0, trim_zeros=True, **kwargs):
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
            return intcomma('{:.2f}'.format(data[self.field] / 100.0))
        except (KeyError, TypeError):
            return '0.00'


class ReportBuilderCurrencyColumn(CurrencyColumn):

    def row_result(self, data, _page_data):
        try:
            return intcomma('{:.2f}'.format(data[self.field]))
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
            render_replace(html='<span style="display: inline-block; width: 60px; height: 15px;'
                                ' background-color: #%1%; vertical-align: middle;"></span>',
                           column=kwargs['column_name'])]
        super().__init__(**kwargs)


class FilterForeignKeyColumn(ColumnBase):
    def get_query_options(self):
        values = self.model.objects.distinct(self.field).order_by(self.field).values_list(self.field, flat=True)
        return {v: v for v in values if v}


class ReverseForeignKeyStrFieldColumn(ColumnBase):
    def __init__(self, field_name, report_builder_class_name, **kwargs):
        if not self.initialise(locals()):
            return
        super().__init__(**kwargs)
        self.field_name = field_name
        self.report_builder_class_name = report_builder_class_name

    def setup_annotations(self, delimiter, sub_filter=None, field_name=None):
        if field_name is None:
            field_name = self.field_name
        self.annotations = {field_name: StringAgg(self.field_name,
                                                  delimiter=delimiter,
                                                  distinct=True,
                                                  filter=sub_filter)}


class ReverseForeignKeyBoolFieldColumn(ColumnBase):
    def __init__(self, field_name, report_builder_class_name, **kwargs):
        if not self.initialise(locals()):
            return
        super().__init__(**kwargs)
        self.field_name = field_name
        self.report_builder_class_name = report_builder_class_name

    def setup_annotations(self, annotations_type, sub_filter=None, field_name=None):
        from advanced_report_builder.globals import ANNOTATION_BOOLEAN_XOR, ANNOTATION_BOOLEAN_AND, \
            ANNOTATION_BOOLEAN_ARRAY
        if field_name is None:
            field_name = self.field_name


        if annotations_type == ANNOTATION_BOOLEAN_XOR:
            self.annotations = {field_name: BoolOr(Cast(self.field_name, BooleanField()),
                                                   filter=sub_filter)}
        elif annotations_type == ANNOTATION_BOOLEAN_AND:
            self.annotations = {field_name: BoolAnd(Cast(self.field_name, BooleanField()),
                                                    filter=sub_filter)}
        elif annotations_type == ANNOTATION_BOOLEAN_ARRAY:
            self.annotations = {field_name: ArrayAgg(self.field_name,
                                                     distinct=True,
                                                     filter=sub_filter)}


class ReverseForeignKeyChoiceFieldColumn(ColumnBase):
    def __init__(self, field_name, report_builder_class_name, **kwargs):
        if not self.initialise(locals()):
            return
        super().__init__(**kwargs)
        self.field_name = field_name
        self.report_builder_class_name = report_builder_class_name

    def setup_annotations(self, sub_filter=None, field_name=None):
        if field_name is None:
            field_name = self.field_name

        self.annotations = {field_name: ArrayAgg(self.field_name,
                                                 distinct=True,
                                                 filter=sub_filter)}


class ReportBuilderColumnLink(ColumnLink):
    """ Sometimes you may want to have a report where the links don't work.
    This is used for when you have a wall board"""

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, url_name):
        if (not self.table or
                self.table.view is None or
                self.table.view.kwargs.get('enable_links') or
                getattr(self.table.view, 'enable_links', False)):
            self._url = get_url(url_name)
        else:
            self._url = f'#?{DUMMY_ID}'


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
