from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('advanced_report_builder', '0034_dashboard_order'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='dashboard',
            options={'get_latest_by': 'created', 'ordering': ('order', 'name', 'id')},
        ),
    ]
