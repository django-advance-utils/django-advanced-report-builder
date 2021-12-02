import copy

from ajax_helpers.mixins import AjaxHelpers
from django.db.models import Sum, Avg
from django.views.generic import TemplateView
from django_datatables.datatables import ColumnInitialisor, DatatableView, DatatableTable, HorizontalTable
from django_menus.menu import MenuMixin

from advanced_report_builder.columns import ReportBuilderNumberColumn
from advanced_report_builder.filter_query import FilterQueryMixin
from advanced_report_builder.globals import NUMBER_FIELDS, ANNOTATION_FUNCTIONS
from advanced_report_builder.models import SingleValueReport
from advanced_report_builder.utils import split_slug


class SingleValueView(AjaxHelpers, FilterQueryMixin, MenuMixin, TemplateView):
    number_field = ReportBuilderNumberColumn
    template_name = 'advanced_report_builder/single_value.html'

    def __init__(self, *args, **kwargs):
        self.slug = None
        self.single_value_report = None
        super().__init__(*args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        self.slug = split_slug(kwargs.get('slug'))
        self.single_value_report = kwargs.get('report').singlevaluereport
        return super().dispatch(request, *args, **kwargs)

    def extra_filters(self, query):
        report_query = self.get_report_query(report=self.single_value_report)
        if not report_query:
            return query

        return self.process_filters(query=query,
                                    search_filter_data=report_query.query)

    @staticmethod
    def _get_count(query):
        return len(query)

    def get_number_field(self, fields, field_name, col_type_override, aggregations_type, decimal_places=0):

        if col_type_override:
            field = copy.deepcopy(col_type_override)
            if aggregations_type == 'count':
                new_field_name = f'{aggregations_type}_{field_name}'
                number_function_kwargs = {}
                function = ANNOTATION_FUNCTIONS[aggregations_type]
                number_function_kwargs['annotations'] = {new_field_name: function(field.field)}

                number_function_kwargs.update({'field': new_field_name,
                                               'column_name': field_name})
                field = self.number_field(**number_function_kwargs)
            else:
                if aggregations_type:
                    new_field_name = f'{aggregations_type}_{field_name}'

                    function = ANNOTATION_FUNCTIONS[aggregations_type]
                    field.aggregations = {new_field_name: function(field.field)}
                    field.field = new_field_name
                    field.options['calculated'] = True

            fields.append(field)
        else:
            number_function_kwargs = {}
            if decimal_places:
                number_function_kwargs = {'decimal_places': int(decimal_places)}

            if aggregations_type:
                new_field_name = f'{aggregations_type}_{field_name}'
                function = ANNOTATION_FUNCTIONS[aggregations_type]
                number_function_kwargs['aggregations'] = {new_field_name: function(field_name)}
                field_name = new_field_name

            number_function_kwargs.update({'field': field_name,
                                           'column_name': field_name})

            field = self.number_field(**number_function_kwargs)
            fields.append(field)

        return field_name

    def _get_sum(self, fields):
        field = self.single_value_report.field
        base_modal = self.single_value_report.get_base_modal()

        original_column_initialisor = ColumnInitialisor(start_model=base_modal, path=field)
        cols = original_column_initialisor.get_columns()
        django_field = original_column_initialisor.django_field
        col_type_override = None

        if django_field is None and cols:
            col_type_override = cols[0]
            column_initialisor = ColumnInitialisor(start_model=base_modal, path=col_type_override.field)
            column_initialisor.get_columns()
            django_field = column_initialisor.django_field
        if isinstance(django_field, NUMBER_FIELDS):
            self.get_number_field(fields=fields,
                                  field_name=field,
                                  col_type_override=col_type_override,
                                  aggregations_type='sum')
        else:
            assert False, 'not a number field'

    def _get_average(self, query):
        field = self.single_value_report.field
        decimal_places = self.single_value_report.decimal_places
        result = query.aggregate(avg=Avg(field))
        if decimal_places == 0:
            avg = int(round(result['avg'], 0))
        else:
            avg = round(result['avg'], decimal_places)
        return avg

    def process_query_results(self):
        single_value_type = self.single_value_report.single_value_type
        fields = []
        if single_value_type == SingleValueReport.SINGLE_VALUE_TYPE_COUNT:
            pass
        elif single_value_type == SingleValueReport.SINGLE_VALUE_TYPE_SUM:
            self._get_sum(fields=fields)
        elif single_value_type == SingleValueReport.SINGLE_VALUE_TYPE_COUNT_AND_SUM:
            pass
        elif single_value_type == SingleValueReport.SINGLE_VALUE_TYPE_AVERAGE:
            pass
        elif single_value_type == SingleValueReport.SINGLE_VALUE_TYPE_PERCENT:
            assert False
        return fields

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # context['query_results'] = self.process_query_results()
        base_modal = self.single_value_report.get_base_modal()

        table = HorizontalTable(model=base_modal)
        table.extra_filters = self.extra_filters
        fields = self.process_query_results()
        table.add_columns(
            *fields
        )

        context['datatable'] = table
        context['single_value_report'] = self.single_value_report
        return context
