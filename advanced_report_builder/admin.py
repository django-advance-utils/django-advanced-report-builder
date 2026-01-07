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
    MultiCellStyle,
    MultiValueReport,
    MultiValueReportCell,
    MultiValueReportColumn,
    PieChartReport,
    Report,
    ReportOption,
    ReportQuery,
    ReportTag,
    ReportType,
    SingleValueReport,
    TableReport,
    Target,
    TargetColour,
)


@admin.register(ReportOption)
class ReportOptionAdmin(admin.ModelAdmin):
    list_display = ('report', 'name')


@admin.register(ReportQuery)
class ReportQueryAdmin(admin.ModelAdmin):
    list_display = ('report', 'name', 'query')


class ReportQueryInline(admin.TabularInline):
    model = ReportQuery


class ReportOptionInline(admin.TabularInline):
    model = ReportOption


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
    inlines = [ReportQueryInline, ReportOptionInline]


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


class TargetColourInline(admin.TabularInline):
    model = TargetColour


@admin.register(Target)
class TargetAdmin(admin.ModelAdmin):
    inlines = [TargetColourInline]
    list_display = ('pk', 'name', 'target_type', 'default_value')


class MultiCellStyleInline(admin.TabularInline):
    model = MultiCellStyle
    extra = 0


class MultiValueReportColumnInline(admin.TabularInline):
    model = MultiValueReportColumn
    extra = 0
    fields = ('column', 'width_type', 'width')
    ordering = ('column',)


class MultiValueReportCellInline(admin.TabularInline):
    model = MultiValueReportCell
    extra = 0
    fields = (
        'row',
        'column',
        'col_span',
        'row_span',
        'multi_value_type',
        'text',
        'multi_cell_style',
        'report_type',
        'field',
        'numerator',
        'prefix',
        'decimal_places',
        'show_breakdown',
        'breakdown_fields',
        'average_scale',
        'average_start_period',
        'average_end_period',
        'label',
        'query_data',
        'extra_query_data',
    )
    ordering = ('row', 'column')


@admin.register(MultiValueReport)
class MultiValueReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'rows', 'columns', 'default_multi_cell_style')
    inlines = [
        MultiCellStyleInline,
        MultiValueReportColumnInline,
        MultiValueReportCellInline,
    ]


@admin.register(MultiCellStyle)
class MultiCellStyleAdmin(admin.ModelAdmin):
    list_display = ('name', 'multi_value_report', 'align_type', 'bold', 'italic', 'font_size')
    list_filter = ('multi_value_report', 'align_type', 'bold', 'italic')
    search_fields = ('name',)


@admin.register(MultiValueReportColumn)
class MultiValueReportColumnAdmin(admin.ModelAdmin):
    list_display = ('multi_value_report', 'column', 'width_type', 'width')
    list_filter = ('multi_value_report', 'width_type')
    ordering = ('multi_value_report', 'column')


@admin.register(MultiValueReportCell)
class MultiValueReportCellAdmin(admin.ModelAdmin):
    list_display = ('multi_value_report', 'row', 'column', 'multi_value_type', 'multi_cell_style')
    list_filter = ('multi_value_report', 'multi_value_type')
    search_fields = ('text', 'label')
