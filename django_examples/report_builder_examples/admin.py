from django.contrib import admin
from report_builder_examples.models import Company, Person, Tags

from report_builder.admin import setup_report_builder_admin


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name',
                    )


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ('first_name',
                    'surname',
                    'company',
                    'date_entered'
                    )


@admin.register(Tags)
class TagsAdmin(admin.ModelAdmin):
    list_display = ('tag',
                    )


setup_report_builder_admin('report_builder_examples', 'Report')
