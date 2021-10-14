from django.db import models
from django.db.models import Count
from django_datatables.model_def import DatatableModel
from django_datatables.columns import ColumnLink, DatatableColumn, ChoiceColumn
from time_stamped_model.models import TimeStampedModel

from report_builder.models import Report
from report_builder.report_builder import ReportBuilderFields


class Sector(TimeStampedModel):
    name = models.CharField(max_length=80)


class Company(TimeStampedModel):
    name = models.CharField(max_length=80)
    active = models.BooleanField(default=False)
    importance = models.IntegerField(null=True)
    sector = models.ForeignKey(Sector, blank=True, null=True, on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = 'Companies'

    class Datatable(DatatableModel):
        people = {'annotations': {'people': Count('person__id')}}
        collink_1 = ColumnLink(title='Defined in Model', field='name', url_name='report_builder_examples:company')

        class Tags(DatatableColumn):
            def setup_results(self, request, all_results):
                tags = Tags.objects.values_list('company__id', 'id')
                tag_dict = {}
                for t in tags:
                    tag_dict.setdefault(t[0], []).append(t[1])
                all_results['tags'] = tag_dict

            @staticmethod
            def proc_result(data_dict, page_results):
                return page_results['tags'].get(data_dict['id'], [])

            def col_setup(self):
                self.options['render'] = [
                    {'var': '%1%', 'html': '%1%', 'function': 'ReplaceLookup'},
                ]
                self.options['lookup'] = list(Tags.objects.values_list('id', 'tag'))
                self.row_result = self.proc_result

    class ReportBuilder(ReportBuilderFields):
        colour = '#00008b'
        title = 'Company'
        fields = ['name',
                  'active',
                  'importance',
                  'people',
                  ('sector__name', {'title': 'Sector Name'}),
                  'collink_1',
                  'created',
                  'modified']

    def __str__(self):
        return self.name


class Person(models.Model):

    class Datatable(DatatableModel):
        title_model = ChoiceColumn('title', choices=((0, 'Mr'), (1, 'Mrs'), (2, 'Miss')))

    title_choices = ((0, 'Mr'), (1, 'Mrs'), (2, 'Miss'))
    title = models.IntegerField(choices=title_choices, null=True)
    company = models.ForeignKey(Company,  on_delete=models.CASCADE)
    first_name = models.CharField(max_length=80)
    surname = models.CharField(max_length=80)
    date_entered = models.DateField(auto_now_add=True)

    class ReportBuilder(ReportBuilderFields):
        colour = '#FF0000'
        title = 'Person'
        fields = ['title',
                  'first_name',
                  'surname',
                  'date_entered']
        includes = [{'prefix': 'company__',
                     'title_prefix': 'Company -> ',
                     'model': 'report_builder_examples.Company.ReportBuilder'}]


class Tags(models.Model):
    tag = models.CharField(max_length=40)
    company = models.ManyToManyField(Company, blank=True)


class Note(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    date = models.DateField()
    notes = models.TextField()


class ExtraReportFields(models.Model):
    report = models.OneToOneField(Report, primary_key=True, on_delete=models.CASCADE)
    notes = models.TextField()
