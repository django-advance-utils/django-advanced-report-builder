# Generated by Django 3.2.7 on 2022-03-11 14:49

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('report_builder_examples', '0003_auto_20220302_1033'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='user_profile',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
    ]
