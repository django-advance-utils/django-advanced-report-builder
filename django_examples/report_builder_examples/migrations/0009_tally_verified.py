# Generated by Django 5.0.7 on 2024-11-05 11:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('report_builder_examples', '0008_contract'),
    ]

    operations = [
        migrations.AddField(
            model_name='tally',
            name='verified',
            field=models.BooleanField(default=False),
        ),
    ]