from django.contrib import admin
from report_builder_examples.models import Company, Person, Tags, Sector, Tally, Payment


@admin.register(Sector)
class SectorAdmin(admin.ModelAdmin):
    list_display = ('name',
                    )


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name',
                    'active',
                    )


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ('title',
                    'first_name',
                    'surname',
                    'company',
                    'date_entered'
                    )


@admin.register(Tags)
class TagsAdmin(admin.ModelAdmin):
    list_display = ('tag',
                    )


@admin.register(Tally)
class TallyAdmin(admin.ModelAdmin):
    list_display = ('date',
                    'cars',
                    'vans',
                    'buses',
                    'lorries',
                    'motor_bikes',
                    'push_bikes',
                    'tractors')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('date',
                    'company',
                    'amount')
