# from show_src_code.apps import PypiAppConfig
#
#
# class AjaxConfig(PypiAppConfig):
#     default = True
#     name = 'report_builder_examples'
#     # pypi = 'django-advance-query-builder'
#     urls = 'report_builder_examples.urls'


from django.apps import AppConfig


class ReportBuilderExamplesConfig(AppConfig):
    default_auto_field = 'django.db.models.AutoField'
    name = 'report_builder_examples'
    verbose_name = 'Report builder examples'

    def ready(self):
        # noinspection PyUnresolvedReferences
        import report_builder_examples.handlers