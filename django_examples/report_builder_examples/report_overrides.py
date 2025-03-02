from django_datatables.columns import ColumnBase


class CustomDateColumn(ColumnBase):
    @staticmethod
    def setup_results(request, all_results):
        all_results['date_format'] = '%d/%m/%y'

    def row_result(self, data, _page_data):
        field = self.field
        if isinstance(field, list):
            field = field[-1]
        try:
            date = data[field].strftime(_page_data['date_format'])
            return date
        except AttributeError:
            return ''
