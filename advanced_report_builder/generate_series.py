from django.db.models import Func
from django.db.models.expressions import RawSQL


class GenerateSeries(Func):
    function = 'GENERATE_SERIES'

    def __init__(self, start_date_field, end_date_field, interval='1 month', output_field=None):
        expressions = [
            start_date_field,
            end_date_field,
            RawSQL('%s', [interval]),
        ]
        super().__init__(*expressions, output_field=output_field)
