from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('advanced_report_builder', '0029_add_prefix_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='tablereport',
            name='allow_new_version',
            field=models.BooleanField(default=False),
        ),
    ]
