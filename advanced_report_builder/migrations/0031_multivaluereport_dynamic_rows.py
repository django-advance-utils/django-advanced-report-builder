import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('advanced_report_builder', '0030_tablereport_allow_new_version'),
    ]

    operations = [
        migrations.AddField(
            model_name='multivaluereport',
            name='dynamic_rows',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='multivaluereport',
            name='dynamic_row_report_type',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='dynamic_multi_value_reports',
                to='advanced_report_builder.reporttype',
            ),
        ),
        migrations.AddField(
            model_name='multivaluereport',
            name='dynamic_row_date_field',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='multivaluereport',
            name='dynamic_row_period',
            field=models.PositiveSmallIntegerField(
                choices=[(1, 'Year'), (2, 'Quarter'), (3, 'Month'), (4, 'Week'), (5, 'Day')], default=4
            ),
        ),
        migrations.AddField(
            model_name='multivaluereport',
            name='dynamic_row_base_query',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='multivaluereport',
            name='dynamic_row_template_row',
            field=models.PositiveSmallIntegerField(default=2),
        ),
        migrations.AddField(
            model_name='multivaluereport',
            name='dynamic_row_label_format',
            field=models.CharField(default='%d/%m/%Y', max_length=32),
        ),
        migrations.AddField(
            model_name='multivaluereport',
            name='dynamic_row_limit',
            field=models.PositiveSmallIntegerField(default=60),
        ),
        migrations.AddField(
            model_name='multivaluereport',
            name='dynamic_row_descending',
            field=models.BooleanField(default=False),
        ),
    ]
