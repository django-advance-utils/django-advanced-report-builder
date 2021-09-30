import csv
import datetime
from report_builder_examples import models


def import_data(path):
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
