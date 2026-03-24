from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('advanced_report_builder', '0027_tablereport_record_nav'),
    ]

    operations = [
        migrations.AddField(
            model_name='reportquery',
            name='denominator_query',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='multivaluereportcell',
            name='denominator_query_data',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
