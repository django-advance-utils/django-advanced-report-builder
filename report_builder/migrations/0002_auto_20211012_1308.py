# Generated by Django 3.2.7 on 2021-10-12 13:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('report_builder', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='reporttype',
            name='report_builder_class_name',
            field=models.CharField(default=' ', max_length=200),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='report',
            name='instance_type',
            field=models.CharField(max_length=255, null=True),
        ),
    ]
