from django_datatables.columns import ColumnBase


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
        try:
            number = self.decimal_places.format(data[self.field])
            return number
        except AttributeError:
            return ""
