# Generated by Django 3.2.7 on 2021-12-03 11:31

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('advanced_report_builder', '0004_auto_20211203_1110'),
    ]

    operations = [
        migrations.RenameField(
            model_name='report',
            old_name='held_slug',
            new_name='slug_alias',
        ),
    ]