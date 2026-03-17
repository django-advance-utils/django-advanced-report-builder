from django.template.loader import render_to_string


class RecordNavPlugin:
    def __init__(self, datatable, title=''):
        self.datatable = datatable
        self.title = title

    def render(self):
        return render_to_string(
            'advanced_report_builder/datatables/record_nav_plugin.html',
            {'datatable': self.datatable, 'nav_title': self.title},
        )
