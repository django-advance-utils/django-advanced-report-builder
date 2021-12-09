import csv
import datetime

from django.contrib.contenttypes.models import ContentType
from report_builder_examples import models

from advanced_report_builder.models import ReportType


def import_data(path):
    import_companies(path)
    import_tallies(path)
    import_report_types()


def import_companies(path):
    if models.Company.objects.all().count() > 0:
        return
    with open(path + '/data/test_data.csv', 'r') as f:
        titles = {c[1]: c[0] for c in models.Person.title_choices}
        csv_reader = csv.DictReader(f)
        for r in csv_reader:

            companies = models.Company.objects.filter(name=r['Company'])
            if len(companies) > 1:
                for c in companies[1:]:
                    c.delete()

            company = models.Company.objects.get_or_create(name=r['Company'])[0]
            models.Person.objects.get_or_create(company=company,
                                                first_name=r['First Name'],
                                                surname=r['Surname'],
                                                title=titles.get(r['Title'], None),
                                                date_entered=datetime.datetime.strptime(r['date_entered'],
                                                                                        '%d/%m/%Y'))
            for tag in r['tags'].split(','):
                if tag != '':
                    tag = models.Tags.objects.get_or_create(tag=tag)[0]
                    tag.company.add(company)


def import_tallies(path):
    with open(path + '/data/test_tallies_data.csv', 'r') as f:
        csv_reader = csv.DictReader(f)
        for r in csv_reader:
            models.Tally.objects.get_or_create(date=datetime.datetime.strptime(r['Date'], '%d/%m/%Y'),
                                               cars=int(r['Cars']),
                                               vans=int(r['Vans']),
                                               buses=int(r['Buses']),
                                               lorries=int(r['Lorries']),
                                               motor_bikes=int(r['Motor Bikes']),
                                               push_bikes=int(r['Push Bikes']),
                                               tractors=int(r['Tractors']))


def import_report_types():

    report_types = [['payment', 'Payment', 'ReportBuilder'],
                    ['tally', 'Tally', 'ReportBuilder']]

    for report_type in report_types:
        content_type = ContentType.objects.get(app_label='report_builder_examples', model=report_type[0])
        ReportType.objects.get_or_create(content_type=content_type,
                                         defaults={'name': report_type[1],
                                                   'report_builder_class_name': report_type[2]})
