# Generated by Django 3.2.7 on 2021-12-01 14:52

from django.db import migrations, models
import django.db.models.deletion
import time_stamped_model.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='Report',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', time_stamped_model.models.CreationDateTimeField(auto_now_add=True)),
                ('modified', time_stamped_model.models.ModificationDateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=200)),
                ('slug', models.SlugField(unique=True)),
                ('instance_type', models.CharField(max_length=255, null=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='SingleValueReport',
            fields=[
                ('report_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='advanced_report_builder.report')),
                ('tile_colour', models.CharField(blank=True, max_length=10, null=True)),
                ('field', models.CharField(blank=True, max_length=200, null=True)),
                ('single_value_type', models.PositiveSmallIntegerField(blank=True, choices=[(1, 'Count'), (2, 'Sum'), (3, 'Count & Sum'), (4, 'Percent'), (5, 'Average')], default=1, null=True)),
                ('decimal_places', models.IntegerField(default=0)),
            ],
            options={
                'abstract': False,
            },
            bases=('advanced_report_builder.report',),
        ),
        migrations.CreateModel(
            name='TableReport',
            fields=[
                ('report_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='advanced_report_builder.report')),
                ('table_fields', models.TextField(blank=True, null=True)),
                ('has_clickable_rows', models.BooleanField(default=False)),
                ('pivot_fields', models.TextField(blank=True, null=True)),
            ],
            options={
                'abstract': False,
            },
            bases=('advanced_report_builder.report',),
        ),
        migrations.CreateModel(
            name='ReportType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', time_stamped_model.models.CreationDateTimeField(auto_now_add=True)),
                ('modified', time_stamped_model.models.ModificationDateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=200)),
                ('report_builder_class_name', models.CharField(max_length=200)),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='contenttypes.contenttype')),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.AddField(
            model_name='report',
            name='report_type',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='advanced_report_builder.reporttype'),
        ),
        migrations.CreateModel(
            name='ReportQuery',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', time_stamped_model.models.CreationDateTimeField(auto_now_add=True)),
                ('modified', time_stamped_model.models.ModificationDateTimeField(auto_now=True)),
                ('name', models.TextField(default='Standard')),
                ('query', models.JSONField(blank=True, null=True)),
                ('extra_query', models.JSONField(blank=True, null=True)),
                ('report', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='advanced_report_builder.report')),
            ],
            options={
                'verbose_name_plural': 'Report queries',
                'ordering': ['name'],
                'unique_together': {('name', 'report')},
            },
        ),
    ]
