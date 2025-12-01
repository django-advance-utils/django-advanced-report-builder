from django.db.models import Count, ExpressionWrapper, FloatField, Sum
from django.db.models.functions import Coalesce, NullIf

from advanced_report_builder.column_types import NUMBER_FIELDS
from advanced_report_builder.exceptions import ReportError
from advanced_report_builder.globals import (
    ANNOTATION_CHOICE_SUM,
)
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

    def get_percentage_field(
        self,
        fields,
        numerator_field_name,
        numerator_col_type_override,
        denominator_field_name,
        denominator_col_type_override,
        numerator_filter,
        decimal_places=0,
    ):
        if numerator_col_type_override:
            actual_numerator_field_name = numerator_col_type_override.field
        else:
            actual_numerator_field_name = numerator_field_name

        if denominator_col_type_override:
            actual_denominator_field_name = denominator_col_type_override.field
        else:
            actual_denominator_field_name = denominator_field_name

        number_function_kwargs = {}
        if decimal_places:
            number_function_kwargs = {'decimal_places': int(decimal_places)}

        new_field_name = f'{actual_numerator_field_name}_{actual_denominator_field_name}'

        if numerator_col_type_override is not None and numerator_col_type_override.annotations:
            if not isinstance(numerator_col_type_override.annotations, dict):
                raise ReportError('Unknown annotation type')

            annotations = list(numerator_col_type_override.annotations.values())[0]
            if numerator_filter and isinstance(annotations, Sum | Count):
                annotations.filter = numerator_filter
                numerator = Coalesce(annotations + 0.0, 0.0)
            else:
                numerator = Coalesce(annotations + 0.0, 0.0)
        else:
            if numerator_filter:
                numerator = Coalesce(
                    (Sum(actual_numerator_field_name, filter=numerator_filter) + 0.0),
                    0.0,
                )
            else:
                numerator = Coalesce((Sum(actual_numerator_field_name) + 0.0), 0.0)

        if denominator_col_type_override is not None and denominator_col_type_override.annotations:
            if not isinstance(denominator_col_type_override.annotations, dict):
                raise ReportError('Unknown annotation type')

            annotations = list(denominator_col_type_override.annotations.values())[0]

            denominator = Coalesce(annotations + 0.0, 0.0)
        else:
            denominator = Coalesce(Sum(actual_denominator_field_name) + 0.0, 0.0)

        number_function_kwargs['aggregations'] = {
            new_field_name: ExpressionWrapper((numerator / NullIf(denominator, 0)) * 100.0, output_field=FloatField())
        }
        field_name = new_field_name

        number_function_kwargs.update(
            {
                'field': field_name,
                'column_name': field_name,
                'options': {'calculated': True},
                'model_path': '',
            }
        )

        field = self.number_field(**number_function_kwargs)

        fields.append(field)

        return field_name

    def _process_percentage(
        self,
        numerator_filter,
        denominator_field,
        numerator_field,
        base_model,
        report_builder_class,
        decimal_places,
        fields,
    ):
        if denominator_field is None:
            raise ReportError('denominator field is None')
        if numerator_field is None:
            raise ReportError('numerator field is None')
        deno_django_field, denominator_col_type_override, _, _ = self.get_field_details(
            base_model=base_model,
            field=denominator_field,
            report_builder_class=report_builder_class,
        )
        if not isinstance(deno_django_field, NUMBER_FIELDS) and (
            denominator_col_type_override is not None and not denominator_col_type_override.annotations
        ):
            raise ReportError('denominator is not a number field')

        num_django_field, numerator_col_type_override, _, _ = self.get_field_details(
            base_model=base_model,
            field=numerator_field,
            report_builder_class=report_builder_class,
        )

        if not isinstance(num_django_field, NUMBER_FIELDS) and (
            numerator_col_type_override is not None and not numerator_col_type_override.annotations
        ):
            raise ReportError('numerator is not a number field')

        self.get_percentage_field(
            fields=fields,
            numerator_field_name=numerator_field,
            numerator_col_type_override=numerator_col_type_override,
            denominator_field_name=denominator_field,
            denominator_col_type_override=denominator_col_type_override,
            numerator_filter=numerator_filter,
            decimal_places=decimal_places,
        )

    def _process_percentage_from_count(self, numerator_filter, decimal_places, fields):
        if numerator_filter:
            numerator = Coalesce(Count(1, filter=numerator_filter) + 0.0, 0.0)
        else:
            numerator = Coalesce(Count(1) + 0.0, 0.0)
        denominator = Coalesce(Count(1) + 0.0, 0.0)
        a = (numerator / denominator) * 100.0

        number_function_kwargs = {
            'aggregations': {'count': a},
            'field': 'count',
            'column_name': 'count',
            'options': {'calculated': True},
            'model_path': '',
        }
        if decimal_places:
            number_function_kwargs['decimal_places'] = int(decimal_places)

        field = self.number_field(**number_function_kwargs)
        fields.append(field)
