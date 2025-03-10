"""django_examples URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView, TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path(
        'favicon.ico',
        RedirectView.as_view(url='/static/report_builder_examples/favicon.ico', permanent=True),
    ),
    path(
        'advanced-report-builder/',
        include('advanced_report_builder.urls', namespace='advanced_report_builder'),
    ),
    path(
        'test/',
        TemplateView.as_view(template_name='report_builder_examples/test.html'),
        name='test',
    ),
    path('', include('report_builder_examples.urls', namespace='report_builder_examples')),
    path('__debug__/', include('debug_toolbar.urls')),
]
