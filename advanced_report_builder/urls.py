from django.urls import path

from advanced_report_builder.views.dashboard import DashboardReportModal, DashboardModal, DashboardAddReportModal
from advanced_report_builder.views.datatables import TableModal, FieldModal
from advanced_report_builder.views.single_values import SingleValueModal

app_name = 'advanced_report_builder'


urlpatterns = [
    path('table/modal/<str:slug>/', TableModal.as_view(), name='table_modal'),
    path('table/modal/field/<str:slug>/', FieldModal.as_view(), name='field_modal'),

    path('single-value/modal/<str:slug>/', SingleValueModal.as_view(), name='single_value_modal'),

    path('dashboard/report/<str:slug>/', DashboardReportModal.as_view(), name='dashboard_report_modal'),
    path('dashboard/<str:slug>/', DashboardModal.as_view(), name='dashboard_modal'),
    path('dashboard/add/<str:slug>/', DashboardAddReportModal.as_view(), name='add_dashboard_report'),

]
