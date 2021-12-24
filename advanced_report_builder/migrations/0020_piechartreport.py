# Generated by Django 3.2.7 on 2021-12-23 11:43

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('advanced_report_builder', '0019_linechartreport'),
    ]

    operations = [
        migrations.CreateModel(
            name='PieChartReport',
            fields=[
                ('report_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='advanced_report_builder.report')),
                ('axis_value_type', models.PositiveSmallIntegerField(blank=True, choices=[(1, 'Sum'), (2, 'Max'), (3, 'Min'), (4, 'Count'), (5, 'Avg')], default=4, null=True)),
                ('fields', models.TextField(blank=True, null=True)),
                ('style', models.PositiveSmallIntegerField(choices=[(1, 'Pie'), (2, 'Doughnut')], default=1)),
            ],
            options={
                'abstract': False,
            },
            bases=('advanced_report_builder.report',),
        ),
    ]