from django.contrib import admin
from advanced_report_builder.models import Report, ReportType, TableReport, ReportQuery


@admin.register(ReportQuery)
class ReportQueryAdmin(admin.ModelAdmin):
    model = ReportQuery
    list_display = ('report',
                    'name',
                    'query')


class ReportQueryInline(admin.TabularInline):
    model = ReportQuery


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('name',
                    'instance_type',
                    )
    inlines = [ReportQueryInline]


@admin.register(ReportType)
class ReportTypeAdmin(admin.ModelAdmin):
    list_display = ('name',
                    'content_type',
                    'report_builder_class_name')


@admin.register(TableReport)
class ReportTableAdmin(admin.ModelAdmin):
    list_display = ('name',
                    )
    exclude = ['instance_type',
               ]
    inlines = [ReportQueryInline]




