from django.db.models import Count

from advanced_report_builder.column_types import NUMBER_FIELDS
from advanced_report_builder.exceptions import ReportError
from advanced_report_builder.globals import ANNOTATION_CHOICE_SUM
from advanced_report_builder.views.charts_base import ChartBaseView


class ValueBaseView(ChartBaseView):
    use_annotations = False

    def _get_count(self, fields):
        number_function_kwargs = {
            'aggregations': {'count': Count(1)},
            'field': 'count',
            'column_name': 'count',
            'options': {'calculated': True},
            'model_path': '',
        }

        field = self.number_field(**number_function_kwargs)
        fields.append(field)

    def _process_aggregations(
        self,
        field,
        base_model,
        report_builder_class,
        decimal_places,
        fields,
        aggregations_type=ANNOTATION_CHOICE_SUM,
        divider=None,
    ):
        django_field, col_type_override, _, _ = self.get_field_details(
            base_model=base_model,
            field=field,
            report_builder_class=report_builder_class,
        )

        if isinstance(django_field, NUMBER_FIELDS) or col_type_override is not None and col_type_override.annotations:
            self.get_number_field(
                annotations_type=aggregations_type,
                append_annotation_query=False,
                index=0,
                data_attr={},
                table_field={'field': field, 'title': field},
                fields=fields,
                col_type_override=col_type_override,
                decimal_places=decimal_places,
                convert_currency_fields=True,
                divider=divider,
            )
        else:
            raise ReportError('not a number field')
