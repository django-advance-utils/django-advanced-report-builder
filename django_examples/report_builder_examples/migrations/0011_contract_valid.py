# Generated by Django 5.0.7 on 2025-02-27 21:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('report_builder_examples', '0010_userprofile_colour'),
    ]

    operations = [
        migrations.AddField(
            model_name='contract',
            name='valid',
            field=models.BooleanField(default=False),
        ),
    ]
