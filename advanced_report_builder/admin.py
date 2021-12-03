from django.contrib import admin
from advanced_report_builder.models import Report, ReportType, TableReport, ReportQuery, SingleValueReport, Dashboard, \
    DashboardReport


@admin.register(ReportQuery)
class ReportQueryAdmin(admin.ModelAdmin):
    list_display = ('report',
                    'name',
                    'query')


class ReportQueryInline(admin.TabularInline):
    model = ReportQuery


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('name',
                    'instance_type',
                    'slug',
                    'slug_alias',
                    )
    exclude = ('slug',
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
                    'slug',
                    )
    exclude = ('instance_type',
               'slug',
               )
    inlines = [ReportQueryInline]


@admin.register(SingleValueReport)
class SingleValueAdmin(admin.ModelAdmin):
    list_display = ('name',
                    'slug',
                    )
    exclude = ('instance_type',
               'slug',
               )
    inlines = [ReportQueryInline]


class DashboardReportInline(admin.TabularInline):
    model = DashboardReport


@admin.register(Dashboard)
class DashboardAdmin(admin.ModelAdmin):

    list_display = ('name',
                    )

    exclude = ['slug',
               ]

    inlines = [DashboardReportInline]