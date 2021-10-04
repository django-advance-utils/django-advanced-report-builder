from django.urls import path

from report_builder_examples.views.reports import ViewReport, ViewReports

app_name = 'report_builder_examples'


urlpatterns = [

    path('', ViewReports.as_view(), name='index'),
    path('<int:pk>/', ViewReport.as_view(), name='view_report')
]
