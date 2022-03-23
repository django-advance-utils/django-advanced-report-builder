class ReportBuilderFields:
    colour = None
    title = None
    fields = []
    pivot_fields = {}
    exclude_search_fields = set()
    exclude_display_fields = set()
    order_by_fields = set()
    url = None
    includes = []
    default_columns = []

    default_multiple_column_text = ''
    default_multiple_column_fields = []
