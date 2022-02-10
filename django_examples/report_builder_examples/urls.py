from django.urls import path
from django.views.generic import TemplateView
from report_builder_examples.views.dashboards import ViewDashboards, ViewDashboard

from report_builder_examples.views.reports import ViewReport, ViewReports, TableExtraModal


app_name = 'report_builder_examples'


urlpatterns = [

    path('example_link/<int:pk>',
         TemplateView.as_view(template_name='report_builder_examples/example_link.html'), name='example_link'),
    path('', ViewReports.as_view(), name='index'),
    path('report/<str:slug>/', ViewReport.as_view(), name='view_report'),
    path('report/table/edit/<str:slug>/', TableExtraModal.as_view(), name='table_extra_modal'),
    path('dashboards/', ViewDashboards.as_view(), name='dashboards_index'),
    path('dashboards/<str:slug>/', ViewDashboard.as_view(), name='view_dashboard'),
    path('dashboards/edit/<str:slug>/', ViewDashboard.as_view(enable_edit=True), name='edit_dashboard'),


]
