from django.db import models
from django.test import SimpleTestCase

from advanced_report_builder.exceptions import ReportError
from advanced_report_builder.field_access import (
    check_filter_path,
    clear_offered_paths,
    offered_field_paths,
)
from advanced_report_builder.report_builder import ReportBuilderFields


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


class ReverseForeignKeyColumnFilterTests(SimpleTestCase):
    """A reverse foreign key column's own filter (a company's contracts' notes, filtered to some contracts).

    Its rules are written against the contract, the model its relation leads to from the model the column is on.
    Reached through an include -- the company's column on a person report -- that model is the company, not the
    report's. None of this queries the database: the filter is built, not run, and the checks are recorded rather
    than made (working out what a model offers draws its columns, and some of the examples' query) -- which model
    each is made against is the point.
    """

    def setUp(self):
        from unittest import mock

        self.checked = []
        for name in ('check_filter_path', 'check_compared_path'):
            patcher = mock.patch(
                f'advanced_report_builder.filter_query.{name}',
                side_effect=lambda model, name=name, **kwargs: self.checked.append((name, model, kwargs)),
            )
            patcher.start()
            self.addCleanup(patcher.stop)

    @staticmethod
    def column(model_path=''):
        from advanced_report_builder.columns import ReverseForeignKeyStrColumn

        column = ReverseForeignKeyStrColumn(
            column_name='contract_notes',
            field_name='contract__notes',
            report_builder_class_name='report_builder_examples.Contract.ReportBuilder',
        )
        column.model_path = model_path
        return column

    @staticmethod
    def data_attr(*rules, has_filter='1'):
        import json

        from advanced_report_builder.utils import encode_attribute

        data_attr = {'has_filter': has_filter}
        if rules:
            query = {'condition': 'AND', 'rules': list(rules), 'valid': True}
            data_attr['filter'] = encode_attribute(json.dumps(query))
        return data_attr

    @staticmethod
    def views():
        from advanced_report_builder.views.datatables.utils import TableUtilsMixin

        return TableUtilsMixin()

    def rule(self, field, operator='equal', value='x', rule_id=None, data_type='string'):
        return {'id': rule_id or field, 'field': field, 'type': data_type, 'operator': operator, 'value': value}

    def built(self, *rules, base_model=None, model_path='', **kwargs):
        from report_builder_examples.models import Company

        return self.views().reverse_foreign_key_filter(
            col_type_override=self.column(model_path),
            data_attr=self.data_attr(*rules, **kwargs),
            base_model=base_model or Company,
        )

    def test_on_its_own_models_report_it_filters_the_contracts(self):
        from django.db.models import Q

        self.assertEqual(Q(contract__notes='x'), self.built(self.rule('notes')))

    def test_through_an_include_it_is_checked_and_written_from_the_columns_model(self):
        """It used to resolve ``contract`` on the person, which has none, and refuse the whole report."""
        from django.db.models import Q

        from report_builder_examples.models import Contract, Person

        built = self.built(self.rule('notes'), base_model=Person, model_path='company__')

        self.assertEqual(Q(contract__notes='x'), built)
        self.assertEqual([('check_filter_path', Contract, {'path': 'notes'})], self.checked)

    def test_the_column_model_follows_the_include(self):
        from report_builder_examples.models import Company, Person

        self.assertIs(Company, self.views().column_model(base_model=Person, col_type_override=self.column('company__')))
        self.assertIs(Company, self.views().column_model(base_model=Company, col_type_override=self.column()))

    def test_a_filter_saved_with_nothing_in_it_is_no_filter(self):
        """A window saved while its query builder could not load stores ``has_filter-1`` and no filter. It used
        to fail the report with a KeyError."""
        self.assertIsNone(self.built())
        self.assertIsNone(self.built(self.rule('notes'), has_filter='0'))

    def test_field_vs_field_compares_two_fields_of_the_contract(self):
        """The compared field is offered by the column's own query builder, so it is the contract's too. It used to
        be checked against the report's model and refuse the whole report."""
        from django.db.models import F, Q

        from report_builder_examples.models import Contract

        built = self.built(self.rule('start_date', value='end_date', rule_id='start_date__field_vs_field'))

        self.assertEqual(Q(contract__start_date=F('contract__end_date')), built)
        self.assertIn(('check_compared_path', Contract, {'compared': 'end_date'}), self.checked)

    def test_a_day_of_week_rule_filters_rather_than_being_dropped(self):
        """A column's filter has no query to annotate, so the day is a lookup. It used to be ignored, so the
        column showed every contract."""
        from django.db.models import Q

        built = self.built(self.rule('start_date', value=2, rule_id='start_date__variable_day'))

        self.assertEqual(Q(contract__start_date__week_day=2), built)
