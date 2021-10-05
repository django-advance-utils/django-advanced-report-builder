from django.urls import path

from report_builder.views.datatables import TableModal, TableView

app_name = 'report_builder'


urlpatterns = [
    path('table/<int:pk>/', TableView.as_view(), name='table_view'),
    path('table/edit/<str:slug>/', TableModal.as_view(), name='table_modal'),
]
