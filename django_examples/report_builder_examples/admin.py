from django.contrib import admin
from report_builder_examples.models import Company, Person, Tags, Sector


@admin.register(Sector)
class SectorAdmin(admin.ModelAdmin):
    list_display = ('name',
                    )


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

