from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('advanced_report_builder', '0032_reporttype_hidden_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='reportquery',
            name='axis_scale',
            field=models.PositiveSmallIntegerField(blank=True, choices=[(1, 'Year'), (2, 'Quarter'), (3, 'Month'), (4, 'Week'), (5, 'Day')], null=True),
        ),
    ]
