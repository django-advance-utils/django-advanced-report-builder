# Generated by Django 3.2.7 on 2021-12-03 15:36

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('advanced_report_builder', '0006_auto_20211203_1506'),
    ]

    operations = [
        migrations.RenameField(
            model_name='dashboard',
            old_name='display_options',
            new_name='display_option',
        ),
    ]