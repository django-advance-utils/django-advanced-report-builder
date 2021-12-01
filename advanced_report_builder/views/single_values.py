from ajax_helpers.mixins import AjaxHelpers
from django.db.models import Sum, Avg
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView
from django_menus.menu import MenuMixin

from advanced_report_builder.filter_query import FilterQueryMixin
from advanced_report_builder.models import SingleValueReport
from advanced_report_builder.utils import split_slug


class SingleValueView(AjaxHelpers, FilterQueryMixin, MenuMixin, TemplateView):

    template_name = 'advanced_report_builder/single_value.html'

    def __init__(self, *args, **kwargs):
        self.slug = None
        self.single_value_report = None
        super().__init__(*args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        self.slug = split_slug(kwargs.get('slug'))
        return super().dispatch(request, *args, **kwargs)

    @staticmethod
    def _get_count(query):
        return len(query)

    def _get_sum(self, query):
        field = self.single_value_report.field
        result = query.aggregate(sum=Sum(field))
        return result['sum']

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
        base_modal = self.single_value_report.get_base_modal()
        query = base_modal.objects.all()

        report_query = self.get_report_query(report=self.single_value_report)
        if report_query is not None:
            query = self.process_filters(query=query,
                                         search_filter_data=report_query.query)

        return_dict = {}
        if single_value_type == SingleValueReport.SINGLE_VALUE_TYPE_COUNT:
            return_dict['values'] = [self._get_count(query=query)]
        elif single_value_type == SingleValueReport.SINGLE_VALUE_TYPE_SUM:
            return_dict['values'] = [self._get_sum(query=query)]
        elif single_value_type == SingleValueReport.SINGLE_VALUE_TYPE_COUNT_AND_SUM:
            return_dict['values'] = [self._get_count(query=query),
                                     self._get_sum(query=query)]
        elif single_value_type == SingleValueReport.SINGLE_VALUE_TYPE_AVERAGE:
            return_dict['values'] = [self._get_average(query=query)]

        else:
            assert False
        return return_dict

    def get_context_data(self, **kwargs):
        self.single_value_report = get_object_or_404(SingleValueReport, pk=self.slug['pk'])

        context = super().get_context_data(**kwargs)
        context['query_results'] = self.process_query_results()
        context['single_value_report'] = self.single_value_report
        return context
