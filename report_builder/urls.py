from django.urls import path

from report_builder.views.datatables import TableModal, TableView, FieldModal

app_name = 'report_builder'


urlpatterns = [
    path('table/<int:pk>/', TableView.as_view(), name='table_view'),
    path('table/edit/<str:slug>/', TableModal.as_view(), name='table_modal'),
    path('table/edit/field/<str:slug>/', FieldModal.as_view(), name='field_modal'),
]
