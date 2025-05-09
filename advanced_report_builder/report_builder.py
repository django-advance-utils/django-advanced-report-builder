from advanced_report_builder.columns import RecordCountColumn


class ReportBuilderFields:
    colour = None
    title = None
    fields = []
    pivot_fields = {}
    exclude_search_fields = set()
    exclude_display_fields = set()
    order_by_fields = set()
    url = None
    includes = {}
    default_columns = []

    field_classes = {'record_count': RecordCountColumn()}

    default_multiple_column_text = ''
    default_multiple_column_fields = []
    default_multiple_pk = 'id'

    extra_chart_field = ['record_count']
