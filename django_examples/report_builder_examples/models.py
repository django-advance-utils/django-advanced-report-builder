from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Count, Sum
from django_datatables.columns import DatatableColumn, CurrencyPenceColumn, ColumnBase, DateColumn
from django_datatables.model_def import DatatableModel
from time_stamped_model.models import TimeStampedModel

from advanced_report_builder.columns import (ColourColumn, ArrowColumn,
                                             FilterForeignKeyColumn, ReportBuilderColumnLink,
                                             ReportBuilderManyToManyColumn, ReverseForeignKeyStrColumn,
                                             ReverseForeignKeyBoolColumn, ReverseForeignKeyChoiceColumn,
                                             ReverseForeignKeyDateColumn)
from advanced_report_builder.models import Report
from advanced_report_builder.report_builder import ReportBuilderFields
from report_builder_examples.report_overrides import CustomDateColumn


def get_merged_name(default=None, **kwargs):
    merge = ' '.join([n for n in kwargs.values() if n is not None and n != ''])
    return merge if merge != '' else default


class UserProfile(AbstractUser):
    colour = models.CharField(max_length=9, null=True, blank=True)

    class Datatable(DatatableModel):
        class FullNameColumn(DatatableColumn):

            def col_setup(self):
                self.field = ['first_name',
                              'last_name',
                              'username']

            # noinspection PyMethodMayBeStatic
            def row_result(self, data, _page_data):
                first_name = data[self.model_path + 'first_name'] \
                    if data[self.model_path + 'first_name'] is not None else ''
                last_name = data[self.model_path + 'last_name'] \
                    if data[self.model_path + 'last_name'] is not None else ''
                username = data[self.model_path + 'username'] \
                    if data[self.model_path + 'username'] is not None else ''

                return get_merged_name(default=username, first_name=first_name, last_name=last_name)

        full_name = FullNameColumn(title='Name')
        colour_column = ColourColumn(title='Colour', field='colour')

    class ReportBuilder(ReportBuilderFields):
        colour = '#606440'
        title = 'Users'
        fields = ['first_name',
                  'last_name',
                  'username',
                  'full_name',
                  'colour_column']
        default_multiple_column_text = '{username} - {first_name} {last_name}'
        default_multiple_column_fields = ['username',
                                          'first_name',
                                          'last_name']


class Sector(TimeStampedModel):
    name = models.CharField(max_length=80)
    type = models.PositiveSmallIntegerField(default=1)

    def __str__(self):
        return self.name

    class ReportBuilder(ReportBuilderFields):
        colour = '#00008b'
        title = 'Sector'
        fields = ['name',
                  'type']
        default_columns = ['.id']
        default_multiple_column_text = '{name}'
        default_multiple_column_fields = ['name']


class CompanyCategory(TimeStampedModel):
    name = models.CharField(max_length=80)

    def __str__(self):
        return self.name


class Company(TimeStampedModel):
    name = models.CharField(max_length=80)
    active = models.BooleanField(default=False)
    number = models.CharField(max_length=128, blank=True)
    importance = models.IntegerField(null=True)
    sectors = models.ManyToManyField(Sector, blank=True, related_name='companysectors')
    background_colour = models.CharField(max_length=8, default='90EE90')
    text_colour = models.CharField(max_length=8, default='454B1B')
    user_profile = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, blank=True, null=True)
    company_category = models.ForeignKey(CompanyCategory, on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        verbose_name_plural = 'Companies'

    class Datatable(DatatableModel):
        company_number = DatatableColumn(field='number', title='Company Number')
        people = DatatableColumn(annotations={'people': Count('person__id', distinct=True)})

        payments = CurrencyPenceColumn(annotations={'payments': Sum('payment__amount', distinct=True)})

        # people = {'annotations': {'people': Count('person__id')}}
        collink_1 = ReportBuilderColumnLink(title='Col link 1',
                                            field='name',
                                            url_name='report_builder_examples:example_link')

        collink_2 = ReportBuilderColumnLink(title='Col link 2',
                                            field=['id', 'name'],
                                            url_name='report_builder_examples:example_link', width='10px',
                                            link_html='<button class="btn btn-sm btn-outline-dark">'
                                                      '<i class="fas fa-building"></i></button>'
                                            )

        background_colour_column = ColourColumn(title='Background Colour', field='background_colour')
        text_colour_column = ColourColumn(title='Text Colour', field='text_colour')

        # sector_names = ManyToManyColumn(column_name='sectors', field='sectors__name')
        sector_names = ReportBuilderManyToManyColumn(field='sectors__name')

        arrow_icon_column = ArrowColumn(title='Arrow Icon')

        total_contract_amount = CurrencyPenceColumn(annotations={'total_contract_amount': Sum('contract__amount')})
        contract_notes = ReverseForeignKeyStrColumn(
            field_name='contract__notes',
            report_builder_class_name='report_builder_examples.Contract.ReportBuilder')

        contract_valid = ReverseForeignKeyBoolColumn(
            field_name='contract__valid',
            report_builder_class_name='report_builder_examples.Contract.ReportBuilder')

        contract_temperature = ReverseForeignKeyChoiceColumn(
            field_name='contract__temperature',
            report_builder_class_name='report_builder_examples.Contract.ReportBuilder')

        contract_created = ReverseForeignKeyDateColumn(
            field_name='contract__created',
            report_builder_class_name='report_builder_examples.Contract.ReportBuilder')

        class Tags(DatatableColumn):
            def setup_results(self, request, all_results):
                tags = Tags.objects.values_list('company__id', 'id')
                tag_dict = {}
                for t in tags:
                    tag_dict.setdefault(t[0], []).append(t[1])
                all_results['tags'] = tag_dict

            def proc_result(self, data_dict, page_results):
                return page_results['tags'].get(data_dict.get(self.model_path + 'id'), [])

            def col_setup(self):
                self.field = ['id']

                self.options['render'] = [
                    {'var': '%1%', 'html': '%1%', 'function': 'ReplaceLookup'},
                ]
                self.options['lookup'] = list(Tags.objects.values_list('id', 'tag'))
                self.row_result = self.proc_result

        date_created = DateColumn(field='created', title='Date Created')
        date_modified = DateColumn(field='modified', title='Date Modified')
        company_category_column = FilterForeignKeyColumn(field='company_category__name',
                                                         title='Company Category')

        importance_choice = ColumnBase(column_name='importance_choice',
                                       field='importance',
                                       title='Importance Choice',
                                       choices={1: 'High', 2: 'Medium', 3: 'Low'})

    class ReportBuilder(ReportBuilderFields):
        colour = '#00008b'
        title = 'Company'

        @property
        def fields(self):
            return ['company_category_column',
                    'arrow_icon_column',
                    'name',
                    'active',
                    'company_number',
                    'importance',
                    'importance_choice',
                    'people',
                    'collink_1',
                    'collink_2',
                    'payments',
                    'sector_names',
                    'date_created',
                    'date_modified',
                    'background_colour_column',
                    'text_colour_column',
                    'Tags',
                    'total_contract_amount',
                    'contract_notes',
                    'contract_valid',
                    'contract_temperature',
                    'contract_created',
                    ]

        default_columns = ['.id']
        default_multiple_column_text = '{name}'
        default_multiple_column_fields = ['name']


        @property
        def includes(self):
            return {'companyinformation': {'title': 'Company Information',
                                           'model': 'report_builder_examples.CompanyInformation.ReportBuilder',
                                           'reversed': True,
                                           'allow_pivots': False},
                    'user_profile': {'title': 'User',
                                     'model': 'report_builder_examples.UserProfile.ReportBuilder'}}

        @property
        def pivot_fields(self):
            return {'tags': {'title': 'Tags',
                             'type': 'tag',
                             'field': 'Tags',
                             'kwargs': {'collapsed': False}},
                    'importance_choice': {'title': 'Importance choice',
                                          'type': 'pivot',
                                          'field': 'importance_choice',
                                          'kwargs': {'collapsed': False}}
                    }

    def __str__(self):
        return self.name


class CompanyInformation(models.Model):
    company = models.OneToOneField(Company, primary_key=True,
                                   related_name='companyinformation', on_delete=models.CASCADE)
    value = models.IntegerField()
    incorporated_date = models.DateField()

    class Datatable(DatatableModel):
        company_value = CurrencyPenceColumn(column_name='company_value', field='value')
        id = ColumnBase(column_name='id', field='company__id', hidden=True)

    class ReportBuilder(ReportBuilderFields):
        colour = '#F0008b'
        title = 'Company Information'
        fields = ['company_value',
                  'incorporated_date']

        default_columns = ['.id']
        includes = {'company': {'title': 'Company',
                                'model': 'report_builder_examples.Company.ReportBuilder'}}

        @property
        def pivot_fields(self):
            return {'incorporated_date': {'title': 'Importance Date',
                                          'type': 'pivot',
                                          'field': 'incorporated_date',
                                          'kwargs': {'collapsed': False}}
                    }


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
        includes = {'company': {'title': 'Company',
                                'model': 'report_builder_examples.Company.ReportBuilder'}}


class Tags(models.Model):
    tag = models.CharField(max_length=40)
    company = models.ManyToManyField(Company, blank=True)

    class Meta:
        verbose_name_plural = 'Tags'


class Note(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    date = models.DateField()
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
    verified = models.BooleanField(default=False)
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        verbose_name_plural = 'Tallies'

    class ReportBuilder(ReportBuilderFields):
        default_columns = ['.id']
        colour = '#006400'
        title = 'Tally'
        fields = ['id',
                  'date',
                  'cars',
                  'vans',
                  'buses',
                  'lorries',
                  'push_bikes',
                  'tractors',
                  'verified']

        includes = {'user_profile': {'title': 'User',
                                     'model': 'report_builder_examples.UserProfile.ReportBuilder'}}


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
        # modified_field = CustomDateColumn(column_name='modified_field', field='modified', title='Modified')

    class ReportBuilder(ReportBuilderFields):
        colour = '#006440'
        title = 'Payment'
        fields = ['date',
                  'currency_amount',
                  'quantity',
                  'received',
                  'created_field',
                  CustomDateColumn(column_name='modified', field='modified', title='Modified'),
                  ]
        includes = {'company': {'title': 'Company',
                                'model': 'report_builder_examples.Company.ReportBuilder'},
                    'user_profile': {'title': 'User',
                                     'model': 'report_builder_examples.UserProfile.ReportBuilder'}}


class Contract(TimeStampedModel):
    TEMPERATURE_TYPES = ((0, 'Cold'), (1, 'Warm'), (2, 'Hot'))

    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    notes = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField()
    amount = models.IntegerField()
    valid = models.BooleanField(default=False)
    temperature = models.IntegerField(choices=TEMPERATURE_TYPES, default=0)

    class Datatable(DatatableModel):
        currency_amount = CurrencyPenceColumn(column_name='currency_amount', field='amount')

    class ReportBuilder(ReportBuilderFields):
        colour = '#406440'
        title = 'Payment'
        fields = ['notes',
                  'start_date',
                  'end_date',
                  'currency_amount',
                  'valid',
                  'temperature']

        includes = {'company': {'title': 'Company',
                                'model': 'report_builder_examples.Company.ReportBuilder'}}


class ReportPermission(TimeStampedModel):
    report = models.OneToOneField(Report, primary_key=True, on_delete=models.CASCADE)
    requires_superuser = models.BooleanField(default=False)
