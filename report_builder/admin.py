from django.contrib import admin
from report_builder.models import Report, ReportType, TableReport


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('name',
                    'instance_type',
                    )


@admin.register(ReportType)
class ReportTypeAdmin(admin.ModelAdmin):
    list_display = ('name',
                    'content_type')


@admin.register(TableReport)
class ReportTableAdmin(admin.ModelAdmin):
    list_display = ('name',
                    )
    exclude = ['instance_type',
               ]
