# Generated by Django 3.2.7 on 2022-01-20 10:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('advanced_report_builder', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='barchartreport',
            name='date_field',
            field=models.CharField(default=' ', max_length=200),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='linechartreport',
            name='date_field',
            field=models.CharField(default=' ', max_length=200),
            preserve_default=False,
        ),
    ]