from django.urls import path
import report_builder_examples.views as views
# from django.views.generic import RedirectView

app_name = 'report_builder_examples'


urlpatterns = [
    # path('', RedirectView.as_view(pattern_name='ajax_main', )),
    # path('ajax-redirect/', RedirectView.as_view(pattern_name='ajax_main', ), name='django-ajax-helpers'),
    # path('ajax_example', views.Example1.as_view(), name='ajax_main'),
    # path('redirect', views.Example2.as_view(), name='redirect'),
    path('datatable/<int:pk>/', views.DatatableReportView.as_view(), name='datatable_report_view')
]
