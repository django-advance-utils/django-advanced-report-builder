import datetime
import json
from unittest import mock

from django.db import models
from django.db.models import F, Q
from django.test import SimpleTestCase, TestCase
from django_datatables.datatables import DatatableTable

from advanced_report_builder.exceptions import ReportError
from advanced_report_builder.field_access import (
    check_filter_path,
    clear_offered_paths,
    offered_field_paths,
)
from advanced_report_builder.report_builder import ReportBuilderFields
from advanced_report_builder.utils import encode_attribute
from advanced_report_builder.views.datatables.utils import TableUtilsMixin
from advanced_report_builder.views.modals_base import QueryBuilderModalBaseMixin
from report_builder_examples.models import Company, Contract, Person


# Declared here rather than in models.py, so they have no migration and no table: working out the offered paths
# never queries the database.
class InheritedParent(models.Model):
    name = models.CharField(max_length=10)

    class Meta:
        app_label = 'report_builder_examples'

    class ReportBuilder(ReportBuilderFields):
        title = 'Inherited parent'
        colour = '#ffffff'
        # Named from the parent's side: they resolve from InheritedParent but not from InheritedChild, which
        # inherits this ReportBuilder.
        fields = ['name', 'inheritedchild__extra']


class InheritedChild(InheritedParent):
    extra = models.CharField(max_length=10)

    class Meta:
        app_label = 'report_builder_examples'


class InheritedReportBuilderTests(SimpleTestCase):
    """A multi-table child drawn with its parent's ReportBuilder offers what it can reach and refuses the rest."""

    def setUp(self):
        clear_offered_paths()
        self.addCleanup(clear_offered_paths)

    def test_the_child_offers_the_fields_it_can_reach(self):
        paths = offered_field_paths(InheritedChild, InheritedChild.ReportBuilder)
        self.assertIn('name', paths)
        self.assertNotIn('inheritedchild__extra', paths)

    def test_the_child_can_be_filtered_on_a_field_it_can_reach(self):
        check_filter_path(InheritedChild, 'name')

    def test_the_child_refuses_a_filter_on_the_parents_accessor(self):
        with self.assertRaises(ReportError):
            check_filter_path(InheritedChild, 'inheritedchild__extra')

    def test_the_parent_still_offers_both(self):
        paths = offered_field_paths(InheritedParent, InheritedParent.ReportBuilder)
        self.assertIn('name', paths)
        self.assertIn('inheritedchild__extra', paths)


def rule(field, operator='equal', value='x', rule_id=None, data_type='string'):
    return {'id': rule_id or field, 'field': field, 'type': data_type, 'operator': operator, 'value': value}


def column_filter(*rules):
    """A reverse foreign key column's settings as its window saves them, with its own filter of ``rules``."""
    query = {'condition': 'AND', 'rules': list(rules), 'valid': True}
    return f'has_filter-1-filter-{encode_attribute(json.dumps(query))}'


class ReverseForeignKeyColumnFilterTests(TestCase):
    """A reverse foreign key column's own filter: a company's contracts' notes, filtered to some contracts.

    Its rules are written against the contract, the model its relation leads to from the model the column is on.
    Reached through an include -- the company's column on a person report -- that model is the company, not the
    report's, and the filter has to be led there from the person, as the column's field is.
    """

    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(name='Acme')
        cls.person = Person.objects.create(company=cls.company, first_name='Ann', surname='Smith')
        # 2 Jan 2023 was a Monday (week_day 2), 3 Jan a Tuesday.
        cls.contract(notes='alpha', start_date=datetime.date(2023, 1, 2), end_date=datetime.date(2023, 1, 2))
        cls.contract(notes='beta', start_date=datetime.date(2023, 1, 3), end_date=datetime.date(2023, 2, 1))

    @classmethod
    def contract(cls, **kwargs):
        return Contract.objects.create(company=cls.company, amount=1, **kwargs)

    def cell(self, base_model, field, data_attr, pk):
        """The column's value for row ``pk`` on a report of ``base_model``, built as a table report builds it."""
        table = DatatableTable('report', model=base_model)
        TableUtilsMixin().process_query_results(
            report_builder_class=base_model.ReportBuilder,
            table=table,
            base_model=base_model,
            fields_used=set(),
            fields_map={},
            table_fields=[{'field': field, 'title': 'Notes', 'data_attr': data_attr}],
        )
        (column,) = [column for column in table.columns if getattr(column, 'annotations', None)]
        ((key, annotation),) = column.annotations.items()
        return base_model.objects.annotate(**{key: annotation}).values_list(key, flat=True).get(pk=pk)

    def company_cell(self, *rules):
        return self.cell(Company, 'contract_notes', column_filter(*rules), self.company.pk)

    def person_cell(self, *rules):
        return self.cell(Person, 'company__contract_notes', column_filter(*rules), self.person.pk)

    def test_on_its_own_models_report_it_filters_the_contracts(self):
        self.assertEqual('alpha', self.company_cell(rule('notes', value='alpha')))

    def test_through_an_include_it_filters_the_contracts(self):
        """It used to resolve ``contract`` on the person, which has none, and refuse the whole report; then to be
        checked on the contract but run from the person without the include's path, and fail the query."""
        self.assertEqual('beta', self.person_cell(rule('notes', value='beta')))

    def test_a_field_the_contract_does_not_offer_is_refused(self):
        with self.assertRaises(ReportError):
            self.person_cell(rule('created', value='2023-01-02', data_type='date'))

    def test_field_vs_field_compares_two_fields_of_the_contract(self):
        """The compared field is offered by the column's own query builder, so it is the contract's too."""
        same_day = rule('start_date', value='end_date', rule_id='start_date__field_vs_field')

        self.assertEqual('alpha', self.company_cell(same_day))
        self.assertEqual('alpha', self.person_cell(same_day))
        self.assertEqual('beta', self.person_cell({**same_day, 'operator': 'not_equal'}))

    def test_a_compared_field_the_contract_does_not_offer_is_refused(self):
        with self.assertRaises(ReportError):
            self.person_cell(rule('start_date', value='created', rule_id='start_date__field_vs_field'))

    def test_a_day_of_week_rule_filters_rather_than_being_dropped(self):
        """A column's filter has no query to annotate, so the day is a lookup. It used to be ignored, so the
        column showed every contract."""
        monday = rule('start_date', value=2, rule_id='start_date__variable_day')

        self.assertEqual('alpha', self.person_cell(monday))
        self.assertEqual('beta', self.person_cell({**monday, 'operator': 'not_equal'}))

    def test_a_filter_saved_with_nothing_in_it_shows_every_contract(self):
        """A window saved while its query builder could not load stores ``has_filter-1`` and no filter. It used
        to fail the report with a KeyError."""
        cell = self.cell(Person, 'company__contract_notes', 'has_filter-1', self.person.pk)

        self.assertEqual(['alpha', 'beta'], sorted(cell.split(', ')))

    def test_an_empty_rule_group_is_no_filter(self):
        self.assertEqual(['alpha', 'beta'], sorted(self.person_cell().split(', ')))


class ReverseForeignKeyColumnFilterPathTests(SimpleTestCase):
    """How the column's filter is led from the report's model to the column's own."""

    @staticmethod
    def column(model_path):
        return mock.Mock(model_path=model_path)

    def test_the_column_model_follows_the_include(self):
        self.assertIs(
            Company, TableUtilsMixin.column_model(base_model=Person, col_type_override=self.column('company__'))
        )
        self.assertIs(Company, TableUtilsMixin.column_model(base_model=Company, col_type_override=self.column('')))

    def test_a_path_that_leads_nowhere_is_a_report_error(self):
        for base_model, model_path in ((Person, 'surname__'), (Person, 'nothing__'), (None, 'company__')):
            with self.subTest(model_path=model_path), self.assertRaises(ReportError):
                TableUtilsMixin.column_model(base_model=base_model, col_type_override=self.column(model_path))

    def test_negation_nesting_and_compared_fields_are_led_from_the_include(self):
        condition = ~(Q(contract__notes='x') | Q(contract__start_date=F('contract__end_date')))

        prefixed = TableUtilsMixin.prefixed_condition(condition, 'company__')

        self.assertEqual(
            ~(Q(company__contract__notes='x') | Q(company__contract__start_date=F('company__contract__end_date'))),
            prefixed,
        )


class QueryBuilderFieldsTests(SimpleTestCase):
    def test_a_field_offered_twice_is_offered_once(self):
        """The query builder refuses a list with an id in it twice and draws nothing."""

        def offered(base_model, query_builder_filters, report_builder_class):
            query_builder_filters.extend([{'id': 'notes'}, {'id': 'start_date'}, {'id': 'notes'}])

        picker = QueryBuilderModalBaseMixin()
        with mock.patch.object(picker, '_get_query_builder_fields', side_effect=offered):
            fields = picker.get_query_builder_fields(base_model=Contract, report_builder_class=Contract.ReportBuilder)

        self.assertEqual(['notes', 'start_date'], [field['id'] for field in fields])
