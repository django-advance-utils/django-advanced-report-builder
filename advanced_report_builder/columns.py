from django.contrib.humanize.templatetags.humanize import intcomma
from django_datatables.columns import ColumnBase, CurrencyPenceColumn, CurrencyColumn, NoHeadingColumn


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

    def __init__(self, *,  decimal_places=0, **kwargs):
        if not self.initialise(locals()):
            return
        super().__init__(**kwargs)
        self.decimal_places = f'{{:.{decimal_places}f}}'

    def row_result(self, data, _page_data):
        number = data.get(self.field)
        if number is None:
            return ''
        else:
            number = self.decimal_places.format(data[self.field])
        if '.' in number:
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
        kwargs['render'] = [{'html': '<i class="fa fa-angle-right fa-2x"></i>', 'function': 'Html'}]
        kwargs['width'] = '10px'
        super().__init__(**kwargs)
