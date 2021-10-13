from django.urls import path
from django.views.generic import TemplateView

from report_builder_examples.views.reports import ViewReport, ViewReports, TableExtraModal

app_name = 'report_builder_examples'


urlpatterns = [

    path('company/<int:pk>',
         TemplateView.as_view(template_name='report_builder_examples/company.html'), name='company'),
    path('', ViewReports.as_view(), name='index'),
    path('<int:pk>/', ViewReport.as_view(), name='view_report'),
    path('table/edit/<str:slug>/', TableExtraModal.as_view(), name='table_extra_modal'),




]
