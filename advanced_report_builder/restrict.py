"""Let the host narrow every queryset a report reads, for the user looking at it.

A host app with rows some users may not see (a tenant's brands, a sales team's own customers) sets
``ADVANCED_REPORT_BUILDER_RESTRICT_QUERYSET`` to a callable, or the dotted path of one, taking
``(queryset, request)`` and returning the queryset that user may see. The report builder calls it on
every queryset it reads report data from: tables, charts, single values, multi-value cells, kanban and
calendar lanes, custom reports, breakdowns, report options and the filter-by-value lists in the query
builder. Without the setting nothing changes.

The request comes from :class:`ReportBuilderRequestMiddleware`, which the host adds to ``MIDDLEWARE``,
because some of those querysets are built far from any view (a column's option list, say). A caller
that has the request to hand passes it.
"""

import contextvars
from functools import lru_cache

from django.conf import settings
from django.utils.module_loading import import_string

_current_request = contextvars.ContextVar('advanced_report_builder_request', default=None)


class ReportBuilderRequestMiddleware:
    """Hold the request for :func:`restrict_queryset` while the report builder answers it."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = _current_request.set(request)
        try:
            return self.get_response(request)
        finally:
            _current_request.reset(token)


def current_request():
    return _current_request.get()


@lru_cache(maxsize=8)
def _import_hook(path):
    return import_string(path)


def get_restrict_hook():
    hook = getattr(settings, 'ADVANCED_REPORT_BUILDER_RESTRICT_QUERYSET', None)
    if not hook:
        return None
    return _import_hook(hook) if isinstance(hook, str) else hook


def restrict_queryset(queryset, request=None):
    """``queryset`` narrowed by the host's hook for this request, or unchanged when no hook is set."""
    hook = get_restrict_hook()
    if hook is None or queryset is None:
        return queryset
    return hook(queryset, request if request is not None else current_request())
