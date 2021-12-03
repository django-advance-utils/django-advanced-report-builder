# Generated by Django 3.2.7 on 2021-12-03 16:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('advanced_report_builder', '0007_rename_display_options_dashboard_display_option'),
    ]

    operations = [
        migrations.AddField(
            model_name='tablereport',
            name='page_length',
            field=models.PositiveSmallIntegerField(choices=[(10, '10'), (25, '25'), (50, '50'), (100, '100'), (150, '150'), (200, '200')], default=100),
        ),
    ]