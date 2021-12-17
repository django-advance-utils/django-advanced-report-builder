from django_datatables.columns import ColumnBase


class CustomDateColumn(ColumnBase):

    @staticmethod
    def setup_results(request, all_results):
        all_results['date_format'] = '%d/%m/%y'

    def row_result(self, data, _page_data):
        try:
            date = data[self.field].strftime(_page_data['date_format'])
            return date
        except AttributeError:
            return ""