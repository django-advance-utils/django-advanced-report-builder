from django.db import migrations, models


def set_record_nav_true(apps, schema_editor):
    for model_name in ['TableReport', 'SingleValueReport', 'BarChartReport', 'MultiValueReportCell']:
        Model = apps.get_model('advanced_report_builder', model_name)
        Model.objects.all().update(record_nav=True)


class Migration(migrations.Migration):

    dependencies = [
        ('advanced_report_builder', '0026_alter_target_period_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='tablereport',
            name='record_nav',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='singlevaluereport',
            name='record_nav',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='barchartreport',
            name='record_nav',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='multivaluereportcell',
            name='record_nav',
            field=models.BooleanField(default=True),
        ),
        migrations.RunPython(set_record_nav_true, migrations.RunPython.noop),
    ]
