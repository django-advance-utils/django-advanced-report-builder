# Generated by Django 5.0.7 on 2024-11-13 11:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('report_builder_examples', '0009_tally_verified'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='colour',
            field=models.CharField(blank=True, max_length=9, null=True),
        ),
    ]