# Generated by Django 3.2.7 on 2021-12-21 16:44

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('advanced_report_builder', '0013_alter_barchartreport_axis_scale'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='barchartreport',
            name='bar_chart_orientation',
        ),
    ]