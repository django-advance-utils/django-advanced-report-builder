from django.urls import path

from report_builder_examples.views.reports import ViewReport

app_name = 'report_builder_examples'


urlpatterns = [

    path('<int:pk>/', ViewReport.as_view(), name='view_report')
]
