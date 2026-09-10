from django.db.models import Q

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
    # What a generated "multiple columns" column is called when the row it was split on is the
    # NULL one. Splitting a count one-column-per-related-row always turns that column up wherever
    # the relation is nullable -- pieces not yet at a station, orders with no customer -- and
    # without this it is headed by whatever str.format() makes of None, which is the word "None".
    # `null`, not `blank`: in Django's vocabulary blank is the empty string, and an empty related
    # value formats as '' and behaves as it always did.
    default_multiple_column_null_text = ''

    extra_chart_field = ['record_count']

    options_filter = Q()
    option_label = '__str__'
    option_ajax_search = []  # ie ['name__icontains']
