"""Which field paths a saved report may use: the ones its field pickers offer, and nothing else.

A report stores the paths it uses as text (its columns, filters, sort orders, chart and calendar
fields, data merge variables). The pickers offer what the report type's ``ReportBuilder``
declares -- its ``fields``, ``field_classes``, pivots and ``includes`` -- and every stored path
is checked against that same walk before it reaches a query:

* :func:`check_field_path` for anything resolved through ``get_field_details`` (columns, charts,
  values, calendars, kanban lanes, sort orders, data merge);
* :func:`check_filter_path` for the query builder's rules, against what the query builder offers;
* :func:`check_mathematical_operand` for the two columns a maths column combines.

A path that fails raises ``ReportError``, which the report views already turn into an error
message on the report instead of a page error.

A ``ReportBuilder`` can stop offering a field that saved reports still name -- it was renamed, or
moved behind another include -- and those reports would then show the error. A host that must keep
them drawing can name a callable in ``REPORT_BUILDER_UNOFFERED_FIELD_PATHS`` (a dotted path, or the
callable itself). It is asked ``(model, path, kind)`` about each path that is not offered, ``kind``
being ``'field'`` or ``'filter'``, and a true answer lets that path through. It is never asked about
a path that is offered.

The offered sets are worked out once per (model, ``ReportBuilder`` class) and kept, since a
``ReportBuilder`` is a class declaration. A host whose ``ReportBuilder`` classes offer different
fields at different times can call :func:`clear_offered_paths` when that changes.
"""

import contextvars
from functools import cache

from django.apps import apps
from django.conf import settings
from django.core.exceptions import FieldDoesNotExist
from django.utils.module_loading import import_string

from advanced_report_builder.exceptions import ReportError

# The maths columns a table offers (``include_mathematical_columns``); they name no model field.
MATHEMATICAL_COLUMNS = frozenset({'rb_addition', 'rb_subtraction', 'rb_times', 'rb_division', 'rb_percentage'})

# Set while an offered set is being worked out: the walk resolves every field it offers through
# get_field_details, which must not check them against the set it is still building.
_offering = contextvars.ContextVar('advanced_report_builder_offering', default=False)


def checks_suspended():
    return _offering.get()


def _model_key(model):
    return model._meta.label


@cache
def _offered_field_paths(model_label, builder_type):
    from advanced_report_builder.field_utils import ReportBuilderFieldUtils

    model = apps.get_model(model_label)
    report_builder_class = builder_type()
    utils = ReportBuilderFieldUtils()
    fields, pivot_fields, include_names = [], [], []
    token = _offering.set(True)
    try:
        utils._get_fields(
            base_model=model,
            fields=fields,
            report_builder_class=report_builder_class,
            pivot_fields=pivot_fields,
            show_order_by_fields=True,
            extra_fields=list(getattr(report_builder_class, 'extra_chart_field', None) or []),
        )
        utils._get_include_names(
            base_model=model,
            fields=include_names,
            report_builder_class=report_builder_class,
            for_select2=False,
        )
    finally:
        _offering.reset(token)
    offered = {entry['field'] for entry in fields + pivot_fields + include_names}
    # The model's own key: a chart counts on it, and it names nothing a row does not already have.
    offered |= {model._meta.pk.name, 'pk'}
    return frozenset(offered | MATHEMATICAL_COLUMNS)


@cache
def _offered_filter_paths(model_label, builder_type):
    from advanced_report_builder.views.modals_base import QueryBuilderModalBaseMixin

    model = apps.get_model(model_label)
    report_builder_class = builder_type()
    filters = []
    token = _offering.set(True)
    try:
        QueryBuilderModalBaseMixin()._get_query_builder_fields(
            base_model=model, query_builder_filters=filters, report_builder_class=report_builder_class
        )
    finally:
        _offering.reset(token)
    fields = {f['field'] for f in filters if f.get('field')}
    compared = set()
    for f in filters:
        if str(f.get('id', '')).endswith('__field_vs_field') and isinstance(f.get('values'), dict):
            compared.update(f['values'])
    return frozenset(fields), frozenset(compared)


@cache
def _model_filter_paths(model_label):
    """What the query builder offers on ``model`` under any of the ``ReportBuilder`` classes it declares.

    A filter is checked by the model it filters, not by one report type: the same saved query reaches the
    ORM from many views (a lane, a cell, a column's own filter), and not all of them know the report type
    the query was built under. Every ``ReportBuilder`` the model declares is one a report type can use."""
    from advanced_report_builder.report_builder import ReportBuilderFields

    model = apps.get_model(model_label)
    fields, compared = set(), set()
    for name in dir(model):
        attr = getattr(model, name, None)
        if isinstance(attr, type) and issubclass(attr, ReportBuilderFields):
            builder_fields, builder_compared = _offered_filter_paths(model_label, attr)
            fields |= builder_fields
            compared |= builder_compared
    return frozenset(fields), frozenset(compared)


def clear_offered_paths():
    _offered_field_paths.cache_clear()
    _offered_filter_paths.cache_clear()
    _model_filter_paths.cache_clear()


def _builder_type(report_builder_class):
    """The ``ReportBuilder`` class, whether its caller passed the class or an instance of it."""
    return report_builder_class if isinstance(report_builder_class, type) else type(report_builder_class)


def offered_field_paths(model, report_builder_class):
    return _offered_field_paths(_model_key(model), _builder_type(report_builder_class))


def _host_allows(model, path, kind):
    """What the host's ``REPORT_BUILDER_UNOFFERED_FIELD_PATHS`` says about a path no picker offers."""
    hook = getattr(settings, 'REPORT_BUILDER_UNOFFERED_FIELD_PATHS', None)
    if not hook:
        return False
    if isinstance(hook, str):
        hook = import_string(hook)
    return bool(hook(model=model, path=path, kind=kind))


def _refuse(path):
    raise ReportError(f'"{path}" is not a field this report can use')


def check_field_path(model, report_builder_class, path):
    """Refuse ``path`` unless the report type's pickers offer it. Anything that is not text (a column
    a ``ReportBuilder`` declares as a class) came from the ``ReportBuilder`` itself and passes."""
    if checks_suspended() or not isinstance(path, str) or report_builder_class is None:
        return
    # Read the declared columns off an instance: a ReportBuilder may declare ``fields`` as a property,
    # and its callers pass the class as often as an instance.
    builder = _builder_type(report_builder_class)()
    if path in builder.field_classes or path in builder.fields:
        return
    path = path.lstrip('-')
    if path not in offered_field_paths(model, report_builder_class) and not _host_allows(model, path, 'field'):
        _refuse(path)


def check_mathematical_operand(model, report_builder_class, operand):
    """Refuse a maths column's operand unless it is a path the report type offers, or the name another column
    of the table gives itself (its column id): a single name that is no field of the model, which the query can
    only resolve as that column's annotation."""
    if checks_suspended() or not isinstance(operand, str) or report_builder_class is None:
        return
    if '__' not in operand:
        try:
            model._meta.get_field(operand)
        except FieldDoesNotExist:
            return
    check_field_path(model=model, report_builder_class=report_builder_class, path=operand)


def check_filter_path(model, path, compared=None):
    """Refuse a query builder rule unless the query builder offers its field on ``model``, and, for a field
    vs field rule, the field it is compared with."""
    if checks_suspended():
        return
    if not isinstance(path, str):
        _refuse(path)
    fields, _ = _model_filter_paths(_model_key(model))
    if path not in fields and not _host_allows(model, path, 'filter'):
        _refuse(path)
    if compared is not None:
        check_compared_path(model, compared)


def check_compared_path(model, compared):
    """Refuse the field a field vs field rule compares with unless the query builder offers it on ``model``."""
    if checks_suspended():
        return
    if not isinstance(compared, str):
        _refuse(compared)
    _, compared_fields = _model_filter_paths(_model_key(model))
    if compared not in compared_fields and not _host_allows(model, compared, 'filter'):
        _refuse(compared)
