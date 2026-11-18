from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('advanced_report_builder', '0033_singlevaluereport_breakdown_order_by'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='dashboard',
            options={'ordering': ('order', 'name', 'id')},
        ),
        migrations.AddField(
            model_name='dashboard',
            name='order',
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
