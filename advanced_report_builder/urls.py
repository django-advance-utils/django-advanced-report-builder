from django.urls import path

from advanced_report_builder.views.dashboard import DashboardReportModal
from advanced_report_builder.views.datatables import TableModal, FieldModal

app_name = 'advanced_report_builder'


urlpatterns = [
    path('table/modal/<str:slug>/', TableModal.as_view(), name='table_modal'),
    path('table/modal/field/<str:slug>/', FieldModal.as_view(), name='field_modal'),
    path('dashboard/<str:slug>/', DashboardReportModal.as_view(), name='dashboard_report_modal'),
]
