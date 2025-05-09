from django.contrib import admin

from advanced_report_builder.models import (
    BarChartReport,
    CustomReport,
    Dashboard,
    DashboardReport,
    FunnelChartReport,
    KanbanReport,
    KanbanReportDescription,
    KanbanReportLane,
    LineChartReport,
    PieChartReport,
    Report,
    ReportQuery,
    ReportTag,
    ReportType,
    SingleValueReport,
    TableReport,
    Target,
)


@admin.register(ReportQuery)
class ReportQueryAdmin(admin.ModelAdmin):
    list_display = ('report', 'name', 'query')


class ReportQueryInline(admin.TabularInline):
    model = ReportQuery


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('name', 'instance_type', 'slug', 'slug_alias', 'version')
    exclude = ('slug',)

    inlines = [ReportQueryInline]


@admin.register(ReportType)
class ReportTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'content_type', 'report_builder_class_name')


@admin.register(TableReport)
class TableReportAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'slug',
    )
    exclude = (
        'instance_type',
        'slug',
    )
    inlines = [ReportQueryInline]


@admin.register(SingleValueReport)
class SingleValueReportAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'slug',
    )
    exclude = (
        'instance_type',
        'slug',
    )
    inlines = [ReportQueryInline]


@admin.register(BarChartReport)
class BarChartReportAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'slug',
    )
    exclude = (
        'instance_type',
        'slug',
    )
    inlines = [ReportQueryInline]


@admin.register(LineChartReport)
class LineChartReportAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'slug',
    )
    exclude = (
        'instance_type',
        'slug',
    )
    inlines = [ReportQueryInline]


@admin.register(PieChartReport)
class PieChartReportAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'slug',
    )
    exclude = (
        'instance_type',
        'slug',
    )
    inlines = [ReportQueryInline]


@admin.register(FunnelChartReport)
class FunnelChartReportAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'slug',
    )
    exclude = (
        'instance_type',
        'slug',
    )
    inlines = [ReportQueryInline]


@admin.register(CustomReport)
class CustomReportAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'output_type', 'view_name', 'settings')
    exclude = ('instance_type', 'slug', 'report_type')


class KanbanReportDescriptionInline(admin.TabularInline):
    model = KanbanReportDescription


class KanbanReportLaneInline(admin.TabularInline):
    model = KanbanReportLane


@admin.register(KanbanReport)
class KanbanReportAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'slug',
    )
    exclude = ('instance_type', 'slug', 'report_type')
    inlines = [KanbanReportLaneInline, KanbanReportDescriptionInline]


class DashboardReportInline(admin.TabularInline):
    model = DashboardReport


@admin.register(Dashboard)
class DashboardAdmin(admin.ModelAdmin):
    list_display = (
        'slug',
        'name',
    )

    exclude = [
        'slug',
    ]

    inlines = [DashboardReportInline]


@admin.register(ReportTag)
class ReportTagAdmin(admin.ModelAdmin):
    list_display = ('name', 'order')


@admin.register(Target)
class TargetAdmin(admin.ModelAdmin):
    list_display = ('pk', 'name', 'target_type', 'default_value')
