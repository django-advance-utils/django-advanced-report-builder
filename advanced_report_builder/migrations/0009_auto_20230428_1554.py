# Generated by Django 3.2.7 on 2023-04-28 15:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('advanced_report_builder', '0008_auto_20220404_1144'),
    ]

    operations = [
        migrations.AddField(
            model_name='singlevaluereport',
            name='average_end_period',
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='singlevaluereport',
            name='average_scale',
            field=models.PositiveSmallIntegerField(blank=True, choices=[(1, 'Year'), (2, 'Quarter'), (3, 'Month'), (4, 'Week'), (5, 'Day')], null=True),
        ),
        migrations.AddField(
            model_name='singlevaluereport',
            name='average_start_period',
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='barchartreport',
            name='axis_value_type',
            field=models.PositiveSmallIntegerField(blank=True, choices=[(1, 'Sum'), (2, 'Maximum'), (3, 'Minimum'), (4, 'Count'), (5, 'Average Sum from Count')], default=4, null=True),
        ),
        migrations.AlterField(
            model_name='funnelchartreport',
            name='axis_value_type',
            field=models.PositiveSmallIntegerField(blank=True, choices=[(1, 'Sum'), (2, 'Maximum'), (3, 'Minimum'), (4, 'Count'), (5, 'Average Sum from Count')], default=4, null=True),
        ),
        migrations.AlterField(
            model_name='linechartreport',
            name='axis_value_type',
            field=models.PositiveSmallIntegerField(blank=True, choices=[(1, 'Sum'), (2, 'Maximum'), (3, 'Minimum'), (4, 'Count'), (5, 'Average Sum from Count')], default=4, null=True),
        ),
        migrations.AlterField(
            model_name='piechartreport',
            name='axis_value_type',
            field=models.PositiveSmallIntegerField(blank=True, choices=[(1, 'Sum'), (2, 'Maximum'), (3, 'Minimum'), (4, 'Count'), (5, 'Average Sum from Count')], default=4, null=True),
        ),
        migrations.AlterField(
            model_name='singlevaluereport',
            name='single_value_type',
            field=models.PositiveSmallIntegerField(choices=[(1, 'Count'), (2, 'Sum'), (3, 'Count & Sum'), (4, 'Percent'), (5, 'Percent from Count'), (6, 'Average Sum from Count'), (7, 'Average Sum over Time')], default=1),
        ),
    ]
