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
