from django.conf import settings


def show_toolbar(request):
    return settings.SHOW_DEBUG_TOOLBAR
