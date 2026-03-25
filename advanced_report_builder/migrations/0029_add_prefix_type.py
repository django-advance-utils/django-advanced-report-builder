from django.db import migrations, models


def migrate_existing_prefixes(apps, schema_editor):
    """Migrate existing records: non-empty prefix -> CUSTOM (2), empty/null -> NONE (1)."""
    SingleValueReport = apps.get_model('advanced_report_builder', 'SingleValueReport')
    SingleValueReport.objects.filter(prefix__isnull=False).exclude(prefix='').update(prefix_type=2)
    SingleValueReport.objects.filter(models.Q(prefix__isnull=True) | models.Q(prefix='')).update(prefix_type=1)

    MultiValueReportCell = apps.get_model('advanced_report_builder', 'MultiValueReportCell')
    MultiValueReportCell.objects.filter(prefix__isnull=False).exclude(prefix='').update(prefix_type=2)
    MultiValueReportCell.objects.filter(models.Q(prefix__isnull=True) | models.Q(prefix='')).update(prefix_type=1)


class Migration(migrations.Migration):

    dependencies = [
        ('advanced_report_builder', '0028_reportquery_denominator_query'),
    ]

    operations = [
        migrations.AddField(
            model_name='singlevaluereport',
            name='prefix_type',
            field=models.PositiveSmallIntegerField(
                choices=[(0, 'Automatic'), (1, 'None'), (2, 'Custom')],
                default=0,
            ),
        ),
        migrations.AddField(
            model_name='multivaluereportcell',
            name='prefix_type',
            field=models.PositiveSmallIntegerField(
                choices=[(0, 'Automatic'), (1, 'None'), (2, 'Custom')],
                default=0,
            ),
        ),
        migrations.RunPython(migrate_existing_prefixes, migrations.RunPython.noop),
    ]
