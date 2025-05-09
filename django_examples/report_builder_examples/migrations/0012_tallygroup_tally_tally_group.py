# Generated by Django 5.0.7 on 2025-03-24 12:28

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('report_builder_examples', '0011_contract_temperature_contract_valid'),
    ]

    operations = [
        migrations.CreateModel(
            name='TallyGroup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('date', models.DateField()),
            ],
        ),
        migrations.AddField(
            model_name='tally',
            name='tally_group',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='report_builder_examples.tallygroup'),
        ),
    ]

