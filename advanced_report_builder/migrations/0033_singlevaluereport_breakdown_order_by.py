from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('advanced_report_builder', '0032_reporttype_hidden_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='singlevaluereport',
            name='breakdown_order_by_field',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='singlevaluereport',
            name='breakdown_order_by_ascending',
            field=models.BooleanField(default=True),
        ),
    ]
