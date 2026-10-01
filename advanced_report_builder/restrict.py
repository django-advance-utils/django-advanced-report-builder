"""Let the host narrow every queryset a report reads, for the user looking at it.

A host app with rows some users may not see (a tenant's brands, a sales team's own customers) sets
``ADVANCED_REPORT_BUILDER_RESTRICT_QUERYSET`` to a callable, or the dotted path of one, taking
``(queryset, request)`` and returning the queryset that user may see. The report builder calls it on
every queryset it reads report rows from: tables, charts, single values, multi-value cells, kanban and
calendar lanes, custom reports, breakdowns, report options and the filter-by-value lists in the query
builder. Without the setting nothing changes.

What it does not narrow: aggregates a report column computes over a *related* model's rows (a reverse
foreign key column, or a sum across a relation). Those follow the restricted base rows, but count every
related row of each one; a host whose restriction is on the related model has to restrict there too.

The request comes from :class:`ReportBuilderRequestMiddleware`, which the host adds to ``MIDDLEWARE``,
because some of those querysets are built far from any view. A caller that has the request to hand
passes it. With a hook set and no request to be found, the hook is still called, with ``None``: a hook
should then return no rows (fail closed), and a warning is logged.
"""

import contextvars
import logging

from asgiref.sync import iscoroutinefunction, markcoroutinefunction
from django.conf import settings
from django.db import models
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)

_current_request = contextvars.ContextVar('advanced_report_builder_request', default=None)


class ReportBuilderRequestMiddleware:
    """Hold the request for :func:`restrict_queryset` while the report builder answers it."""

    sync_capable = True
    async_capable = True

    def __init__(self, get_response):
        self.get_response = get_response
        if iscoroutinefunction(self.get_response):
            markcoroutinefunction(self)

    def __call__(self, request):
        if iscoroutinefunction(self):
            return self.__acall__(request)
        token = _current_request.set(request)
        try:
            return self.get_response(request)
        finally:
            _current_request.reset(token)

    async def __acall__(self, request):
        token = _current_request.set(request)
        try:
            return await self.get_response(request)
        finally:
            _current_request.reset(token)


def current_request():
    return _current_request.get()


def get_restrict_hook():
    hook = getattr(settings, 'ADVANCED_REPORT_BUILDER_RESTRICT_QUERYSET', None)
    if not hook:
        return None
    return import_string(hook) if isinstance(hook, str) else hook


def restrict_queryset(queryset, request=None):
    """``queryset`` narrowed by the host's hook for this request, or unchanged when no hook is set.

    A manager is turned into a queryset first, so the hook is always handed a ``QuerySet``.
    """
    hook = get_restrict_hook()
    if hook is None or queryset is None:
        return queryset
    if isinstance(queryset, models.Manager):
        queryset = queryset.all()
    if request is None:
        request = current_request()
        if request is None:
            logger.warning(
                'ADVANCED_REPORT_BUILDER_RESTRICT_QUERYSET is set but no request was found for a %s queryset: '
                'is ReportBuilderRequestMiddleware in MIDDLEWARE?',
                queryset.model.__name__,
            )
    return hook(queryset, request)


def restricted(view, extra_filters):
    """``extra_filters`` with the restriction applied after it, for wiring onto a table.

    Applied where a view hands its filters to its table, so a subclass that overrides ``extra_filters``
    without calling ``super()`` cannot drop the restriction. Filtering twice is harmless.
    """

    def apply(query):
        return restrict_queryset(extra_filters(query), getattr(view, 'request', None))

    return apply
