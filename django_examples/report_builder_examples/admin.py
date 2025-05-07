from django.contrib import admin
from report_builder_examples.models import (
    Company,
    Person,
    Tags,
    Sector,
    Tally,
    Payment,
    CompanyInformation,
    ReportPermission,
    CompanyCategory,
    Contract,
    TallyGroup,
    TallyTag,

)
from django.contrib.auth.admin import UserAdmin

from report_builder_examples.models import UserProfile
from django.utils.translation import gettext_lazy as _


@admin.register(Sector)
class SectorAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'type',
    )


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'active', 'importance', 'modified', 'user_profile')
    search_fields = ('name',)


@admin.register(CompanyInformation)
class CompanyInformation(admin.ModelAdmin):
    list_display = ('value', 'incorporated_date')


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ('title', 'first_name', 'surname', 'company', 'date_entered')


@admin.register(Tags)
class TagsAdmin(admin.ModelAdmin):
    list_display = ('tag',)


@admin.register(TallyTag)
class TallTagAdmin(admin.ModelAdmin):
    list_display = ('name', )


@admin.register(TallyGroup)
class TallyGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'date')


@admin.register(Tally)
class TallyAdmin(admin.ModelAdmin):
    list_display = (
        'date',
        'tally_group',
        'cars',
        'vans',
        'buses',
        'lorries',
        'motor_bikes',
        'push_bikes',
        'tractors',
        'user_profile',
        'verified',
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('date', 'company', 'amount', 'quantity', 'received', 'user_profile')


@admin.register(UserProfile)
class UserProfileAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (
            _('Permissions'),
            {'fields': ('is_active', 'is_staff', 'is_superuser')},
        ),  # Removed groups + user_permissions
        (_('Important dates'), {'fields': ('colour',)}),
    )


@admin.register(ReportPermission)
class ReportPermissionAdmin(admin.ModelAdmin):
    list_display = ('get_report_name', 'requires_superuser')

    @staticmethod
    def get_report_name(obj):
        return obj.report.name


@admin.register(CompanyCategory)
class CompanyCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ('company', 'start_date', 'end_date', 'amount')
