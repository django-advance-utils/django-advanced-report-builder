from django.contrib import admin
from django.apps import apps

from report_builder.models import MyChild


class ReportAdmin(admin.ModelAdmin):
    list_display = ('name',
                    )


class ReportTypeAdmin(admin.ModelAdmin):
    list_display = ('name',
                    'content_type')


class ReportTableAdmin(admin.ModelAdmin):
    list_display = ('name',
                    )


def setup_report_builder_admin(app_label, model_name):

    report_cls = apps.get_model(app_label=app_label, model_name=model_name)
    admin.site.register(report_cls, ReportAdmin)

    report_type = apps.get_model(app_label=app_label, model_name=f'{model_name}ReportType')
    admin.site.register(report_type, ReportTypeAdmin)

    table_report_cls = apps.get_model(app_label=app_label, model_name=f'{model_name}TableReport')
    admin.site.register(table_report_cls, ReportTableAdmin)


@admin.register(MyChild)
class MyChildAdmin(admin.ModelAdmin):
    list_display = ('name',
                    )
