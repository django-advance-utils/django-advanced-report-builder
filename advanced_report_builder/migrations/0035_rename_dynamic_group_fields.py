from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('advanced_report_builder', '0034_multivaluereportrow_show_blank_dates'),
    ]

    operations = [
        migrations.RenameField(
            model_name='multivaluereportrow',
            old_name='date_field',
            new_name='group_field',
        ),
        migrations.RenameField(
            model_name='multivaluereportcell',
            old_name='period_date_field',
            new_name='group_field',
        ),
    ]
