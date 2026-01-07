import copy

from ajax_helpers.mixins import AjaxHelpers
from crispy_forms.layout import Fieldset
from django.conf import settings
from django.forms import ChoiceField, ModelChoiceField
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import TemplateView
from django_datatables.columns import ColumnNameError
from django_menus.menu import MenuMixin
from django_modals.forms import CrispyForm
from django_modals.modals import FormModal, ModelFormModal
from django_modals.processes import (
    PERMISSION_DISABLE,
    PERMISSION_OFF,
    PROCESS_EDIT_DELETE,
)
from django_modals.widgets.select2 import Select2
from django_modals.widgets.widgets import Toggle

from advanced_report_builder.exceptions import ReportError
from advanced_report_builder.models import (
    Dashboard,
    DashboardReport,
    Report,
    ReportQuery,
)
from advanced_report_builder.utils import (
    get_report_builder_class,
    get_template_type_class,
    get_view_type_class,
    split_slug,
)


class ViewDashboardBase(AjaxHelpers, MenuMixin, TemplateView):
    model = Dashboard
    enable_edit = True
    enable_links = True
    custom_views = {}
    views_overrides = {}
    ajax_commands = ['button', 'select2', 'ajax']

    def __init__(self, *args, **kwargs):
        self.dashboard = None
        self._view_type_class = None
        super().__init__(*args, **kwargs)

    def redirect_url(self):
        """used if the slug changes"""
        return None

    def dashboard_not_found(self):
        raise Http404

    def dispatch(self, request, *args, **kwargs):
        slug = split_slug(self.kwargs['slug'])
        self.dashboard = self.model.objects.filter(slug=slug['pk']).first()

        if self.dashboard is None:
            self.dashboard = self.model.objects.filter(slug_alias=slug['pk']).first()
            if self.dashboard is None:
                return self.dashboard_not_found()
            else:
                redirect_url = self.redirect_url()
                if redirect_url:
                    return redirect_url

        return super().dispatch(request, *args, **kwargs)

    def get_view_types_class(self):
        if self._view_type_class is None:
            self._view_type_class = get_view_type_class()
        return self._view_type_class

    @staticmethod
    def get_top_report_class(reports):
        reports_len = len(reports)
        spans = {
            1: ' col-12',
            2: ' col-12 col-sm-12 col-md-6',
            3: ' col-12 col-sm-12 col-md-4',
            4: ' col-12 col-sm-12 col-md-6 col-lg-3',
            6: ' col-12 col-sm-12 col-md-4',
            9: ' col-12 col-sm-12 col-md-4',
        }
        return spans.get(reports_len, ' col-12 col-sm-12 col-md-3')

    def has_dashboard_permission(self):
        """You can over override this to check if the user has permission to view the dashboard.
        If return false 'dashboard_no_permission' will be called"""
        return True

    def dashboard_no_permission(self):
        raise Http404

    def has_report_got_permission(self, report):
        """You can over override this to check if the user has permission to view the report.
        If return false 'report_no_permission' will be called"""
        return True

    def report_no_permission(self, dashboard_report, reports):
        pass

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dashboard'] = self.dashboard

        if not self.has_dashboard_permission():
            return self.dashboard_no_permission()

        top_reports = []
        reports = []
        for dashboard_report in self.dashboard.dashboardreport_set.all():
            if self.has_report_got_permission(report=dashboard_report.report):
                report_view = self.get_view(report=dashboard_report.report)
                extra_class_name = report_view().get_dashboard_class(report=dashboard_report.report)
                try:
                    report_data = self.call_view(
                        dashboard_report=dashboard_report, report_view=report_view
                    ).rendered_content
                    report = {
                        'render': report_data,
                        'name': dashboard_report.report.name,
                        'id': dashboard_report.id,
                        'class': dashboard_report.get_class(extra_class_name=extra_class_name),
                    }
                except (ReportError, ColumnNameError) as e:
                    report = self.call_error_view(
                        dashboard_report=dashboard_report, extra_class_name=extra_class_name, error_message=e.value
                    )
                if dashboard_report.top:
                    top_reports.append(report)
                else:
                    reports.append(report)

            else:
                self.report_no_permission(dashboard_report=dashboard_report, reports=reports)

        context['top_reports'] = top_reports
        context['top_reports_class'] = self.get_top_report_class(top_reports)

        context['reports'] = reports
        context['enable_edit'] = self.enable_edit
        return context

    def call_error_view(self, dashboard_report, extra_class_name, error_message):
        view_types_class = self.get_view_types_class()
        error_view = (
            self.views_overrides.get('error')
            if 'error' in self.views_overrides
            else view_types_class.views.get('error')
        )
        report_data = self.call_view(
            dashboard_report=dashboard_report, report_view=error_view, extra_kwargs={'error_message': error_message}
        ).rendered_content
        report = {
            'render': report_data,
            'name': dashboard_report.report.name,
            'id': dashboard_report.id,
            'class': dashboard_report.get_class(extra_class_name=extra_class_name),
        }
        return report

    def get_view(self, report):
        view_types_class = self.get_view_types_class()
        if report.instance_type == 'customreport':
            view_name = report.customreport.view_name
            return self.custom_views.get(view_name, view_types_class.custom_views.get(view_name))
        elif report.instance_type in self.views_overrides:
            return self.views_overrides.get(report.instance_type)
        return view_types_class.views.get(report.instance_type)

    def call_view(self, dashboard_report, report_view=None, extra_kwargs=None):
        if report_view is None:
            report_view = self.get_view(report=dashboard_report.report)
        view_kwargs = copy.deepcopy(self.kwargs)
        view_kwargs['report'] = dashboard_report.report
        view_kwargs['dashboard_report'] = dashboard_report
        view_kwargs['enable_edit'] = self.enable_edit
        view_kwargs['enable_links'] = self.enable_links
        view_kwargs['output_type_template'] = self.get_report_template(dashboard_report=dashboard_report)
        view_kwargs['extra_kwargs'] = extra_kwargs
        return report_view.as_view()(self.request, *self.args, **view_kwargs)

    def get_report_template(self, dashboard_report):
        template_types = get_template_type_class()
        return template_types.get_template_name_from_instance_type(
            instance_type=dashboard_report.report.instance_type, template_style=dashboard_report.report.template_style
        )

    def post(self, request, *args, **kwargs):
        table_id = request.POST.get('table_id')
        if table_id:  # must be a datatable:
            dashboard_report_id = table_id.split('_')[1]
            if dashboard_report_id:
                dashboard_report = self.dashboard.dashboardreport_set.filter(id=dashboard_report_id).first()
                return self.call_view(dashboard_report=dashboard_report)

        return super().post(request, *args, **kwargs)

    def ajax_change_placement(self, **kwargs):
        ids = kwargs['ids']
        dashboard_reports = DashboardReport.objects.filter(id__in=ids)
        obj_dict = dict([(obj.id, obj) for obj in dashboard_reports])
        sorted_objects = [obj_dict[_id] for _id in ids]

        for index, dashboard_report in enumerate(sorted_objects):
            if dashboard_report.order != index:
                dashboard_report.order = index
                dashboard_report.save()

        return self.command_response()


class DashboardModal(ModelFormModal):
    model = Dashboard
    form_fields = ['name', 'display_option']
    process = PROCESS_EDIT_DELETE
    permission_delete = PERMISSION_OFF

    def post_save(self, created, form):
        if created:
            url_name = getattr(settings, 'REPORT_BUILDER_DASHBOARD_URL_NAME', '')
            if url_name:
                url = reverse(url_name, kwargs={'slug': self.object.slug})
                self.add_command('redirect', url=url)


class DashboardReportModal(ModelFormModal):
    model = DashboardReport
    process = PROCESS_EDIT_DELETE
    permission_delete = PERMISSION_OFF
    permission_create = PERMISSION_DISABLE

    def __init__(self, *args, **kwargs):
        self._report_options = None
        super().__init__(*args, **kwargs)

    @property
    def form_fields(self):
        fields = ['name_override', 'top', 'display_option']
        report_obj = getattr(self.object.report, self.object.report.instance_type)
        if report_obj.show_dashboard_query():
            fields += [
                'show_versions',
                'report_query',
            ]
        if report_obj.show_options() and len(self.get_report_options()) > 0:
            fields.append('show_options')
        return fields

    widgets = {
        'top': Toggle(attrs={'data-onstyle': 'success', 'data-on': 'YES', 'data-off': 'NO'}),
        'show_versions': Toggle(attrs={'data-onstyle': 'success', 'data-on': 'YES', 'data-off': 'NO'}),
        'show_options': Toggle(attrs={'data-onstyle': 'success', 'data-on': 'YES', 'data-off': 'NO'}),
    }

    def get_report_options(self):
        if self._report_options is None:
            self._report_options = self.object.report.reportoption_set.all()
        return self._report_options

    def form_setup(self, form, *_args, **_kwargs):
        layout = ['name_override', 'top', 'display_option']
        form.add_trigger(
            'top',
            'onchange',
            [
                {
                    'selector': '#div_id_display_option',
                    'values': {'checked': 'hide'},
                    'default': 'show',
                },
            ],
        )
        form.fields[
            'name_override'
        ].help_text = f'Original report name "{self.object.report.name}". Leave blank to keep this name.'
        report_obj = getattr(self.object.report, self.object.report.instance_type)
        report_obj.dashboard_fields(form=form, dashboard_report=self.object, layout=layout)
        if report_obj.show_dashboard_query():
            layout += ['show_versions', 'report_query']
            report_queries = ReportQuery.objects.filter(report=form.instance.report)
            form.fields['report_query'] = ModelChoiceField(queryset=report_queries, widget=Select2, required=False)

        if report_obj.show_options() and len(report_options := self.get_report_options()) > 0:
            layout.append('show_options')
            options = []
            for report_option in report_options:
                field_id = f'option{report_option.id}'

                base_model = report_option.content_type.model_class()
                report_cls = get_report_builder_class(
                    model=base_model, class_name=report_option.report_builder_class_name
                )
                choices = [(0, 'N/A')]
                for _obj in base_model.objects.filter(report_cls.options_filter):
                    method = getattr(_obj, report_cls.option_label, None)
                    label = method() if callable(method) else _obj.__str__()
                    choices.append((_obj.id, label))
                initial = self.object.options.get(field_id) if self.object.options else None
                form.fields[field_id] = ChoiceField(
                    required=False, label=report_option.name, choices=choices, initial=initial
                )
                options.append(field_id)
            if options:
                layout.append(Fieldset('Options', *options))
        return layout

    def form_valid(self, form):
        instance = form.save(commit=False)
        instance._current_user = self.request.user
        report_obj = getattr(self.object.report, self.object.report.instance_type)
        report_obj.save_extra_dashboard_fields(form=form, dashboard_report=instance)
        report_options = self.get_report_options()
        if report_options:
            options = instance.options if instance.options else {}
            for report_option in report_options:
                field_id = f'option{report_option.id}'
                raw_value = form.cleaned_data.get(field_id)
                try:
                    value = int(raw_value or 0)
                except (TypeError, ValueError):
                    value = 0
                if value == 0:
                    if field_id in options:
                        del options[field_id]
                else:
                    options[field_id] = value
            instance.options = options
        instance.save()
        return self.command_response('reload')


class DashboardAddReportModal(FormModal):
    form_class = CrispyForm
    modal_title = 'Add Report'

    def form_setup(self, form, *_args, **_kwargs):
        grouped_choices = {}
        for report in Report.objects.all():
            group_name = report.get_output_type_name()
            grouped_choices.setdefault(group_name, []).append((report.pk, report.name))

        form.fields['report'] = ChoiceField(
            choices=[(group_name, choices) for group_name, choices in grouped_choices.items()], widget=Select2
        )

    def form_valid(self, form):
        dashboard = get_object_or_404(Dashboard, id=self.slug['pk'])
        dashboard_report = DashboardReport(dashboard=dashboard)
        dashboard_report.report_id = form.cleaned_data['report']
        dashboard_report.save()
        return self.command_response('reload')
