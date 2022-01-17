from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Count, Sum
from django_datatables.columns import ColumnLink, DatatableColumn, CurrencyPenceColumn
from django_datatables.model_def import DatatableModel
from report_builder_examples.report_overrides import CustomDateColumn
from time_stamped_model.models import TimeStampedModel

from advanced_report_builder.models import Report
from advanced_report_builder.report_builder import ReportBuilderFields


class UserProfile(AbstractUser):
    class ReportBuilder(ReportBuilderFields):
        colour = '#606440'
        title = 'Users'
        fields = ['first_name',
                  'last_name',
                  'username']
        default_multiple_column_text = '{first_name} {last_name}'
        default_multiple_column_fields = ['first_name',
                                          'last_name']


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
        people = DatatableColumn(annotations={'people': Count('person__id', distinct=True)})

        payments = CurrencyPenceColumn(annotations={'payments': Sum('payment__amount', distinct=True)})

        # people = {'annotations': {'people': Count('person__id')}}
        collink_1 = ColumnLink(title='Defined in Model', field='name', url_name='report_builder_examples:example_link')

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
                  'payments',
                  'created',
                  'modified',
                  ]
        default_columns = ['.id']
        default_multiple_column_text = '{name}'
        default_multiple_column_fields = ['name']

    def __str__(self):
        return self.name


class Person(models.Model):

    title_choices = ((0, 'Mr'), (1, 'Mrs'), (2, 'Miss'))
    title = models.IntegerField(choices=title_choices, null=True)
    company = models.ForeignKey(Company,  on_delete=models.CASCADE, null=True, blank=True)
    first_name = models.CharField(max_length=80)
    surname = models.CharField(max_length=80)
    date_entered = models.DateField(auto_now_add=True)

    class ReportBuilder(ReportBuilderFields):
        colour = '#FF0000'
        title = 'Person'
        fields = ['id',
                  'title',
                  'first_name',
                  'surname',
                  'date_entered']
        includes = [{'field': 'company',
                     'title': 'Company',
                     'model': 'report_builder_examples.Company.ReportBuilder'}]


class Tags(models.Model):
    tag = models.CharField(max_length=40)
    company = models.ManyToManyField(Company, blank=True)

    class Meta:
        verbose_name_plural = 'Tags'


class Note(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    date = models.DateField()
    notes = models.TextField()


class ExtraReportFields(models.Model):
    report = models.OneToOneField(Report, primary_key=True, on_delete=models.CASCADE)
    notes = models.TextField()


class Tally(models.Model):
    date = models.DateField()
    cars = models.IntegerField()
    vans = models.IntegerField()
    buses = models.IntegerField()
    lorries = models.IntegerField()
    motor_bikes = models.IntegerField()
    push_bikes = models.IntegerField()
    tractors = models.IntegerField()

    class Meta:
        verbose_name_plural = 'Tallies'

    class ReportBuilder(ReportBuilderFields):
        colour = '#006400'
        title = 'Tally'
        fields = ['date',
                  'cars',
                  'vans',
                  'buses',
                  'lorries',
                  'push_bikes',
                  'tractors']


class Payment(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    date = models.DateField()
    amount = models.IntegerField()
    quantity = models.IntegerField()
    received = models.BooleanField(default=False)
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, null=True, blank=True)

    class Datatable(DatatableModel):
        currency_amount = CurrencyPenceColumn(column_name='currency_amount', field='amount')
        created_field = CustomDateColumn(column_name='created_field', field='created', title='Created')
        modified_field = CustomDateColumn(column_name='modified_field', field='modified', title='Modified')

    class ReportBuilder(ReportBuilderFields):
        colour = '#006440'
        title = 'Payment'
        fields = ['date',
                  'currency_amount',
                  'quantity',
                  'received',
                  'created_field',
                  'modified_field',
                  ]
        includes = [{'field': 'company',
                     'title': 'Company',
                     'model': 'report_builder_examples.Company.ReportBuilder'},
                    {'field': 'user_profile',
                     'title': 'User',
                     'model': 'report_builder_examples.UserProfile.ReportBuilder'},
                    ]
