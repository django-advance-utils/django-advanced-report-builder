import base64
from urllib.parse import quote, unquote

from ajax_helpers.mixins import AjaxHelpers
from django.core.exceptions import FieldError
from django.db.models import Q
from django.forms import ChoiceField
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django_menus.menu import MenuItem, MenuMixin
from django_modals.forms import CrispyForm
from django_modals.modals import FormModal
from django_modals.widgets.select2 import Select2, select2_ajax_result

from advanced_report_builder.models import ReportOption
from advanced_report_builder.utils import get_report_builder_class, make_slug_str


class ReportBase(AjaxHelpers, MenuMixin):
    max_dropdown_option = 20

    # noinspection PyUnusedLocal
    @staticmethod
    def duplicate_menu(request, report_id):
        return [
            MenuItem(
                f'advanced_report_builder:duplicate_report_modal,pk-{report_id}',
                css_classes=['btn-success'],
            )
        ]

    def get_dashboard_class(self, report):
        return None

    def queries_option_menus(self, report, dashboard_report):
        menus = []

        self._queries_menus(report=report, dashboard_report=dashboard_report, menus=menus)
        self._option_menus(report=report, dashboard_report=dashboard_report, menus=menus)

        return menus

    def _queries_menus(self, report, dashboard_report, menus):
        query_slug = f'query{report.id}'
        if dashboard_report is not None:
            if not dashboard_report.show_versions:
                return
            query_slug += f'_{dashboard_report.id}'
        report_queries = report.reportquery_set.all()
        if len(report_queries) > 1:
            dropdown = []
            for report_query in report_queries:
                slug_str = make_slug_str(self.slug, overrides={query_slug: report_query.id})
                dropdown.append(
                    (
                        self.request.resolver_match.view_name,
                        report_query.name,
                        {'url_kwargs': {'slug': slug_str}},
                    )
                )
            menus.append(
                MenuItem(
                    menu_display='Version',
                    no_hover=True,
                    css_classes='btn-secondary',
                    dropdown=dropdown,
                )
            )

    def _option_menus(self, report, dashboard_report, menus):
        append_option_slug = ''
        dashboard_report_id = 0
        if dashboard_report is not None:
            if not dashboard_report.show_options:
                return
            dashboard_report_id = dashboard_report.id
            append_option_slug = f'_{dashboard_report.id}'
        view_name = self.request.resolver_match.view_name
        for report_option in report.reportoption_set.all():
            option_slug = f'option{report_option.id}{append_option_slug}'
            base_model = report_option.content_type.model_class()
            report_cls = get_report_builder_class(model=base_model, class_name=report_option.report_builder_class_name)
            qs = base_model.objects.filter(report_cls.options_filter)
            # Fetch at most 21 rows
            probe = list(qs[: self.max_dropdown_option + 1])
            if len(probe) <= self.max_dropdown_option:
                slug_str = make_slug_str(self.slug, overrides={option_slug: 0})
                dropdown = [
                    (
                        view_name,
                        'N/A',
                        {'url_kwargs': {'slug': slug_str}},
                    )
                ]
                for _obj in probe:
                    slug_str = make_slug_str(self.slug, overrides={option_slug: _obj.id})
                    method = getattr(_obj, report_cls.option_label, None)
                    label = method() if callable(method) else _obj.__str__()
                    dropdown.append(
                        (
                            view_name,
                            label,
                            {'url_kwargs': {'slug': slug_str}},
                        )
                    )
                menus.append(
                    MenuItem(
                        menu_display=report_option.name,
                        no_hover=True,
                        css_classes='btn-secondary',
                        dropdown=dropdown,
                    )
                )
            else:
                view_name_encoded = quote(base64.b64encode(view_name.encode()).decode(), safe='')
                slug_str = make_slug_str(
                    self.slug,
                    overrides={
                        'report_option': report_option.id,
                        'view_name': view_name_encoded,
                        'dashboard_report_id': dashboard_report_id,
                    },
                )
                menus.append(
                    MenuItem(
                        menu_display=report_option.name,
                        url='advanced_report_builder:select_option_modal',
                        url_slug=slug_str,
                        css_classes='btn-secondary',
                    )
                )


class SelectOptionModal(FormModal):
    form_class = CrispyForm
    max_options = 50

    @property
    def modal_title(self):
        report_option = self.get_report_option()
        return f'Select {report_option.name} option'

    def __init__(self, *args, **kwargs):
        self._report_cls = None
        self._report_option = None
        self._base_model = None
        self._option_slug = None
        super().__init__(*args, **kwargs)

    def get_report_option(self):
        if self._report_option is None:
            self._report_option = get_object_or_404(ReportOption, pk=self.slug['report_option'])
        return self._report_option

    def get_report_class_and_base_model(self):
        if self._report_cls is None:
            report_option = self.get_report_option()
            self._base_model = report_option.content_type.model_class()
            self._report_cls = get_report_builder_class(
                model=self._base_model, class_name=report_option.report_builder_class_name
            )
        return self._report_cls, self._base_model

    def get_option_label(self, obj, report_cls):
        method = getattr(obj, report_cls.option_label, None)
        return method() if callable(method) else obj.__str__()

    def form_setup(self, form, *_args, **_kwargs):
        report_cls, base_model = self.get_report_class_and_base_model()
        option_slug = self.get_option_slug()
        choices = []
        initial = None
        if option_slug in self.slug:
            _obj = base_model.objects.filter(report_cls.options_filter).first()
            if _obj is not None:
                label = self.get_option_label(_obj, report_cls)
                choices.append((_obj.id, label))
                initial = _obj.id

        class MyChoiceField(ChoiceField):
            def validate(self, value):
                return

        form.fields['select_option'] = MyChoiceField(widget=Select2(attrs={'ajax': True}), choices=choices)
        if initial is not None:
            form.fields['select_option'].initial = initial

    def get_option_slug(self):
        if self._option_slug is None:
            dashboard_report_id = int(self.slug['dashboard_report_id'])
            append_option_slug = ''
            if dashboard_report_id != 0:
                append_option_slug = f'_{dashboard_report_id}'
            report_option = self.get_report_option()
            self._option_slug = f'option{report_option.id}{append_option_slug}'
        return self._option_slug

    def form_valid(self, form):
        view_name = base64.b64decode(unquote(self.slug['view_name'])).decode()
        option_slug = self.get_option_slug()
        slug_str = make_slug_str(
            self.slug,
            overrides={option_slug: form.cleaned_data['select_option']},
            excludes=['report_option', 'view_name', 'dashboard_report_id'],
        )
        url = reverse(view_name, kwargs={'slug': slug_str})
        return self.command_response('redirect', url=url)

    def select2_select_option(self, search=None, page=None, **_kwargs):
        report_cls, base_model = self.get_report_class_and_base_model()

        qs = base_model.objects.filter(report_cls.options_filter)

        if search:
            try:
                fields = report_cls.option_ajax_search or []

                if fields:
                    query = Q()
                    for field in fields:
                        query |= Q(**{f'{field}__icontains': search})

                    qs = qs.filter(query)

            except FieldError:
                # Invalid field name → fall back to unfiltered qs
                pass

        qs = qs[: self.max_options]

        new_results = []

        # Add synthetic option (not from DB)
        if not search:
            new_results.append((0, 'N/A'))

        for _obj in qs:
            label = self.get_option_label(_obj, report_cls)
            new_results.append((_obj.id, label))

        return select2_ajax_result(new_results)
