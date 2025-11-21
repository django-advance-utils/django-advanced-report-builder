import json

from django.conf import settings
from django.contrib.humanize.templatetags.humanize import intcomma
from django.core.exceptions import ValidationError, FieldError, FieldDoesNotExist
from django.forms import ChoiceField, ModelChoiceField
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django_datatables.datatables import DatatableTable
from django_menus.menu import MenuItem
from django_modals.fields import FieldEx
from django_modals.form_helpers import HorizontalNoEnterHelper
from django_modals.helper import show_modal
from django_modals.modals import Modal, ModelFormModal
from django_modals.processes import PERMISSION_OFF, PROCESS_EDIT_DELETE
from django_modals.widgets.select2 import Select2, Select2Multiple
from django_modals.widgets.widgets import Toggle

from advanced_report_builder.columns import ReportBuilderNumberColumn
from advanced_report_builder.exceptions import ReportError
from advanced_report_builder.globals import (
    ANNOTATION_CHOICE_AVERAGE_SUM_FROM_COUNT,
    ANNOTATION_CHOICE_SUM,
)
from advanced_report_builder.models import ReportQuery, ReportType, SingleValueReport, Target
from advanced_report_builder.utils import get_report_builder_class
from advanced_report_builder.variable_date import VariableDate
from advanced_report_builder.views.datatables.modal import (
    TableFieldForm,
    TableFieldModal,
)
from advanced_report_builder.views.datatables.utils import TableUtilsMixin
from advanced_report_builder.views.helpers import QueryBuilderModelForm
from advanced_report_builder.views.modals_base import (
    QueryBuilderModalBase,
    QueryBuilderModalBaseMixin,
)
from advanced_report_builder.views.query_modal.mixin import MultiQueryModalMixin
from advanced_report_builder.views.targets.utils import get_target_value
from advanced_report_builder.views.value_base import ValueBaseView


class SingleValueView(ValueBaseView):
    number_field = ReportBuilderNumberColumn
    template_name = 'advanced_report_builder/single_values/report.html'

    def dispatch(self, request, *args, **kwargs):
        self.report = kwargs.get('report')
        self.chart_report = self.report.singlevaluereport
        return super().dispatch(request, *args, **kwargs)

    def report_builder_class(self, base_model):
        report_builder_class = get_report_builder_class(model=base_model, report_type=self.chart_report.report_type)
        return report_builder_class

    def process_query_results(self, base_model, table):
        single_value_type = self.chart_report.single_value_type
        fields = []
        base_model = self.chart_report.get_base_model()
        report_builder_class = self.report_builder_class(base_model)
        if single_value_type == SingleValueReport.SingleValueType.COUNT:
            self._get_count(fields=fields)
        elif single_value_type == SingleValueReport.SingleValueType.SUM:
            self._process_aggregations(
                field=self.chart_report.field,
                report_builder_class=report_builder_class,
                base_model=base_model,
                decimal_places=self.chart_report.decimal_places,
                fields=fields,
                aggregations_type=ANNOTATION_CHOICE_SUM,
            )
        elif single_value_type == SingleValueReport.SingleValueType.COUNT_AND_SUM:
            self._get_count(fields=fields)
            self._process_aggregations(
                field=self.chart_report.field,
                report_builder_class=report_builder_class,
                base_model=base_model,
                decimal_places=self.chart_report.decimal_places,
                fields=fields,
                aggregations_type=ANNOTATION_CHOICE_SUM,
            )
        elif single_value_type == SingleValueReport.SingleValueType.AVERAGE_SUM_FROM_COUNT:
            self._process_aggregations(
                field=self.chart_report.field,
                report_builder_class=report_builder_class,
                base_model=base_model,
                decimal_places=self.chart_report.decimal_places,
                fields=fields,
                aggregations_type=ANNOTATION_CHOICE_AVERAGE_SUM_FROM_COUNT,
            )
        elif single_value_type in [
            SingleValueReport.SingleValueType.AVERAGE_SUM_OVER_TIME,
            SingleValueReport.SingleValueType.AVERAGE_SUM_OVER_TIME_EXCLUDING_WEEKENDS,
        ]:
            exclude_weekdays = None
            if single_value_type == SingleValueReport.SingleValueType.AVERAGE_SUM_OVER_TIME_EXCLUDING_WEEKENDS:
                exclude_weekdays = [1, 7]

            divider = self.get_period_divider(
                annotation_value_choice=self.chart_report.average_scale,
                start_date_type=self.chart_report.average_start_period,
                end_date_type=self.chart_report.average_end_period,
                exclude_weekdays=exclude_weekdays,
            )
            self._process_aggregations(
                field=self.chart_report.field,
                report_builder_class=report_builder_class,
                base_model=base_model,
                decimal_places=self.chart_report.decimal_places,
                fields=fields,
                aggregations_type=ANNOTATION_CHOICE_SUM,
                divider=divider,
            )
        elif single_value_type == SingleValueReport.SingleValueType.PERCENT:
            self._process_percentage(
                denominator_field=self.chart_report.field,
                numerator_field=self.chart_report.numerator,
                report_builder_class=report_builder_class,
                decimal_places=self.chart_report.decimal_places,
                base_model=base_model,
                fields=fields,
            )
        elif single_value_type == SingleValueReport.SingleValueType.PERCENT_FROM_COUNT:
            report_query = self.get_report_query(report=self.chart_report)

            numerator_filter = None
            if report_query:
                numerator_filter = self.process_filters(search_filter_data=report_query.extra_query)

            self._process_percentage_from_count(
                numerator_filter=numerator_filter, decimal_places=self.chart_report.decimal_places, fields=fields
            )
        return fields

    def set_prefix(self):
        self.table.prefix = self.chart_report.prefix
        if self.table.prefix:
            self.table.prefix += ' '

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.set_prefix()
        self.table.single_value = self.chart_report
        self.table.enable_links = self.kwargs.get('enable_links')
        self.table.target_data = self.get_target_data()
        self.table.datatable_template = 'advanced_report_builder/single_values/middle.html'
        self.table.breakdown_url = self.get_breakdown_url()
        context['single_value_report'] = self.chart_report
        return context

    def get_target_data(self):
        report_query = self.get_report_query(report=self.chart_report)
        if report_query is None or report_query.target is None:
            return None

        # this query line need to be at the top otherwise get_month_period doesn't work
        data = self.table.get_table_array(self.kwargs.get('request'), self.table.get_query())
        if len(data) == 0 or len(data[0]) == 0:
            return None
        month = self.period_data.get_month_period()
        if month is None:
            return None  # todo / week targets etc

        target_value = get_target_value(
            min_date=month[0],
            max_date=month[1],
            target=report_query.target,
            month_range=True,
        )
        if target_value is None or target_value == 0:
            return None
        try:
            raw_value = data[0][0]  # Safely inside the try block
            cleaned_value = raw_value.replace(',', '')
            value = float(cleaned_value)
        except (ValueError, TypeError, AttributeError, IndexError):
            return None
        percentage = (value / float(target_value)) * 100
        bar_percentage = min(percentage, 100)

        if report_query.target.target_type == Target.TargetType.MONEY:
            # Format as currency (with commas, and possibly prefix later)
            prefix = self.chart_report.prefix
            target_value = intcomma(f'{float(target_value):.2f}')
            target_value = f'{prefix}&thinsp;' + target_value
        else:
            # Remove trailing .0 if it's a whole number
            if float(target_value).is_integer():
                target_value = str(int(float(target_value)))
            else:
                target_value = f'{float(target_value):.2f}'

        return {
            'target_value': target_value,
            'colour': report_query.target.colour,
            'percentage': percentage,
            'bar_percentage': bar_percentage,
        }

    def get_breakdown_slug(self):
        query_id = self.slug.get(f'query{self.report.pk}')
        if query_id is None and self.dashboard_report is not None:
            query_id = self.dashboard_report.report_query_id
        slug = f'pk-{self.table.single_value.id}-enable_links-{self.table.enable_links}'
        if query_id is not None:
            slug += f'-query{self.report.pk}-{query_id}'
        return slug

    def get_breakdown_url(self):
        if self.table.single_value.show_breakdown:
            slug = self.get_breakdown_slug()
            return show_modal(
                'advanced_report_builder:single_value_show_breakdown_modal',
                slug,
                href=True,
            )
        return None

    def pod_dashboard_view_menu(self):
        return []

    def edit_report_menu(self, request, chart_report_id, slug_str):
        return [
            MenuItem(
                f'advanced_report_builder:single_value_modal,pk-{chart_report_id}{slug_str}',
                menu_display='Edit',
                font_awesome='fas fa-pencil-alt',
                css_classes=['btn-primary'],
            ),
            *self.duplicate_menu(request=request, report_id=chart_report_id),
        ]


class SingleValueModal(MultiQueryModalMixin, QueryBuilderModalBase):
    template_name = 'advanced_report_builder/single_values/modal.html'
    process = PROCESS_EDIT_DELETE
    permission_delete = PERMISSION_OFF
    model = SingleValueReport
    show_order_by = False
    show_target = True
    widgets = {
        'report_tags': Select2Multiple,
        'show_breakdown': Toggle(attrs={'data-onstyle': 'success', 'data-on': 'YES', 'data-off': 'NO'}),
    }

    form_fields = [
        'name',
        'notes',
        'report_type',
        'report_tags',
        ('single_value_type', {'label': 'Value type'}),
        ('numerator', {'label': 'Numerator field'}),
        'average_scale',
        'average_start_period',
        'average_end_period',
        'field',
        'prefix',
        'tile_colour',
        ('decimal_places', {'field_class': 'col-md-5 col-lg-3 input-group-sm'}),
        'show_breakdown',
        'breakdown_fields',
    ]

    def form_setup(self, form, *_args, **_kwargs):
        form.add_trigger(
            'single_value_type',
            'onchange',
            [
                {
                    'selector': '#div_id_field',
                    'values': {
                        SingleValueReport.SingleValueType.COUNT: 'hide',
                        SingleValueReport.SingleValueType.PERCENT_FROM_COUNT: 'hide',
                    },
                    'default': 'show',
                },
                {
                    'selector': '#div_id_prefix',
                    'values': {
                        SingleValueReport.SingleValueType.COUNT: 'hide',
                        SingleValueReport.SingleValueType.PERCENT_FROM_COUNT: 'hide',
                    },
                    'default': 'show',
                },
                {
                    'selector': '#div_id_numerator',
                    'values': {SingleValueReport.SingleValueType.PERCENT: 'show'},
                    'default': 'hide',
                },
                {
                    'selector': 'label[for=id_field]',
                    'values': {
                        SingleValueReport.SingleValueType.PERCENT: (
                            'html',
                            'Denominator field',
                        )
                    },
                    'default': ('html', 'Field'),
                },
                {
                    'selector': '#div_id_average_scale',
                    'values': {
                        SingleValueReport.SingleValueType.AVERAGE_SUM_OVER_TIME: 'show',
                        SingleValueReport.SingleValueType.AVERAGE_SUM_OVER_TIME_EXCLUDING_WEEKENDS: 'show',
                    },
                    'default': 'hide',
                },
                {
                    'selector': '#div_id_average_start_period',
                    'values': {
                        SingleValueReport.SingleValueType.AVERAGE_SUM_OVER_TIME: 'show',
                        SingleValueReport.SingleValueType.AVERAGE_SUM_OVER_TIME_EXCLUDING_WEEKENDS: 'show',
                    },
                    'default': 'hide',
                },
                {
                    'selector': '#div_id_average_end_period',
                    'values': {
                        SingleValueReport.SingleValueType.AVERAGE_SUM_OVER_TIME: 'show',
                        SingleValueReport.SingleValueType.AVERAGE_SUM_OVER_TIME_EXCLUDING_WEEKENDS: 'show',
                    },
                    'default': 'hide',
                },
            ],
        )

        form.add_trigger(
            'show_breakdown',
            'onchange',
            [
                {
                    'selector': '#div_id_breakdown_fields',
                    'values': {'checked': 'show'},
                    'default': 'hide',
                },
            ],
        )

        if 'data' in _kwargs and len(_kwargs['data']) > 0:
            field = _kwargs['data'].get('field')
            numerator = _kwargs['data'].get('numerator')
            report_type_id = _kwargs['data'].get('report_type')
            report_type = get_object_or_404(ReportType, id=report_type_id)
        else:
            field = form.instance.field
            report_type = form.instance.report_type
            numerator = form.instance.numerator

        self.setup_field(
            field_type='number',
            form=form,
            field_name='field',
            selected_field_id=field,
            report_type=report_type,
        )

        self.setup_field(
            field_type='number',
            form=form,
            field_name='numerator',
            selected_field_id=numerator,
            report_type=report_type,
        )

        form.fields['notes'].widget.attrs['rows'] = 3
        url = reverse(
            'advanced_report_builder:single_value_field_modal',
            kwargs={'slug': 'selector-99999-data-FIELD_INFO-report_type_id-REPORT_TYPE_ID'},
        )

        range_type_choices = VariableDate.RANGE_TYPE_CHOICES
        form.fields['average_start_period'] = ChoiceField(required=False, choices=range_type_choices)
        form.fields['average_end_period'] = ChoiceField(required=False, choices=range_type_choices)
        fields = [
            'name',
            'notes',
            'report_type',
            'report_tags',
            'single_value_type',
            'numerator',
            'field',
            'average_scale',
            'average_start_period',
            'average_end_period',
            'prefix',
            'tile_colour',
            'decimal_places',
            'show_breakdown',
            FieldEx(
                'breakdown_fields',
                template='advanced_report_builder/select_column.html',
                extra_context={'select_column_url': url, 'command_prefix': ''},
            ),
        ]
        if self.object.id:
            self.add_extra_queries(form=form, fields=fields)
            if self.object.single_value_type in [
                SingleValueReport.SingleValueType.PERCENT,
                SingleValueReport.SingleValueType.PERCENT_FROM_COUNT,
            ]:
                self.add_page_command('set_css', selector='.btn-query-edit', prop='display', val='none')
            else:
                self.add_page_command(
                    'set_css',
                    selector='.btn-query-numerator-edit',
                    prop='display',
                    val='none',
                )
        return fields

    def select2_field(self, **kwargs):
        return self.get_fields_for_select2(
            field_type='number',
            report_type=kwargs['report_type'],
            search_string=kwargs.get('search'),
        )

    def select2_numerator(self, **kwargs):
        return self.get_fields_for_select2(
            field_type='number',
            report_type=kwargs['report_type'],
            search_string=kwargs.get('search'),
        )

    # noinspection PyUnusedLocal
    def clean(self, form, cleaned_data):
        single_value_type = cleaned_data['single_value_type']
        if (
            single_value_type
            not in [
                SingleValueReport.SingleValueType.COUNT,
                SingleValueReport.SingleValueType.PERCENT_FROM_COUNT,
            ]
            and not cleaned_data['field']
        ):
            raise ValidationError('Please select a field')

        if single_value_type == SingleValueReport.SingleValueType.AVERAGE_SUM_OVER_TIME:
            if cleaned_data['average_scale'] is None:
                form.add_error('average_scale', 'Please select a time scale')
            if cleaned_data['average_start_period'] is None:
                form.add_error('average_start_period', 'Please select a start period')
            if cleaned_data['average_end_period'] is None:
                form.add_error('average_end_period', 'Please select a end period')

    def ajax_get_fields(self, **kwargs):
        report_type_id = kwargs['report_type']
        report_builder_fields, base_model = self.get_report_builder_class(report_type_id=report_type_id)
        fields = []
        tables = []
        self._get_fields(
            base_model=base_model,
            fields=fields,
            tables=tables,
            report_builder_class=report_builder_fields,
        )
        return self.command_response('report_fields', data=json.dumps({'fields': fields, 'tables': tables}))

    def button_add_query(self, **_kwargs):
        single_value_type = _kwargs['single_value_type']
        if single_value_type == '' or int(single_value_type) not in [
            SingleValueReport.SingleValueType.PERCENT,
            SingleValueReport.SingleValueType.PERCENT_FROM_COUNT,
        ]:
            return super().button_add_query(**_kwargs)
        else:
            slug = self.get_query_slug(f'report_id-{self.object.id}', **_kwargs)
            url = reverse(
                'advanced_report_builder:single_value_numerator_modal',
                kwargs={'slug': slug},
            )
            return self.command_response('show_modal', modal=url)

    def button_edit_query(self, **_kwargs):
        single_value_type = _kwargs['single_value_type']
        if single_value_type == '' or int(single_value_type) not in [
            SingleValueReport.SingleValueType.PERCENT,
            SingleValueReport.SingleValueType.PERCENT_FROM_COUNT,
        ]:
            return super().button_edit_query(**_kwargs)
        else:
            query_id = _kwargs['query_id'][1:]
            slug = self.get_query_slug(f'pk-{query_id}', **_kwargs)
            url = reverse(
                'advanced_report_builder:single_value_numerator_modal',
                kwargs={'slug': slug},
            )
            return self.command_response('show_modal', modal=url)

    def query_fields(self):
        return ['name', ('target__name', {'title': 'Target Name'})]

    def form_valid(self, form):
        org_id = self.object.pk if hasattr(self, 'object') else None
        created = org_id is None
        instance = form.save(commit=False)
        instance._current_user = self.request.user
        instance.save()

        if created:
            self.modal_redirect(
                self.request.resolver_match.view_name,
                slug=f'pk-{self.object.id}-new-True',
            )
        else:
            url_name = getattr(settings, 'REPORT_BUILDER_DETAIL_URL_NAME', '')
            if url_name and self.slug.get('new'):
                url = reverse(url_name, kwargs={'slug': self.object.slug})
                self.add_command('redirect', url=url)
        if not self.response_commands:
            self.add_command('reload')

        return self.command_response()


class SingleValueShowBreakdownModal(TableUtilsMixin, Modal):
    button_container_class = 'text-center'
    size = 'xl'

    def modal_title(self):
        return self.table_report.name

    def add_table(self, base_model):
        return DatatableTable(view=self, model=base_model)

    def setup_table(self):
        single_value_report = get_object_or_404(SingleValueReport, pk=self.slug['pk'])
        self.kwargs['enable_links'] = self.slug['enable_links'] == 'True'
        self.table_report = single_value_report
        base_model = single_value_report.get_base_model()
        table = self.add_table(base_model=base_model)
        table.extra_filters = self.extra_filters
        table_fields = single_value_report.breakdown_fields
        report_builder_class = get_report_builder_class(model=base_model, report_type=self.table_report.report_type)
        fields_used = set()
        fields_map = {}
        try:
            self.process_query_results(
                report_builder_class=report_builder_class,
                table=table,
                base_model=base_model,
                fields_used=fields_used,
                fields_map=fields_map,
                table_fields=table_fields,
            )
        except (FieldError, FieldDoesNotExist) as e:
            raise ReportError(e)
        table.ajax_data = False
        table.table_options['pageLength'] = 25
        table.table_options['bStateSave'] = False
        return table

    def modal_content(self):
        table = self.setup_table()
        return table.render()


class SingleValueTableFieldForm(TableFieldForm):
    cancel_class = 'btn-secondary modal-cancel'


class SingleValueTableFieldModal(TableFieldModal):
    form_class = SingleValueTableFieldForm


class QueryNumeratorForm(QueryBuilderModelForm):
    cancel_class = 'btn-secondary modal-cancel'

    class Meta:
        model = ReportQuery
        fields = ['name', 'query', 'extra_query', 'target']

    def setup_modal(self, *args, **kwargs):
        self.fields['extra_query'].label = 'Numerator'
        self.fields['target'] = ModelChoiceField(queryset=Target.objects.all(), widget=Select2, required=False)
        super().setup_modal(*args, **kwargs)


class QueryNumeratorModal(QueryBuilderModalBaseMixin, ModelFormModal):
    model = ReportQuery
    process = PROCESS_EDIT_DELETE
    permission_delete = PERMISSION_OFF
    form_class = QueryNumeratorForm
    helper_class = HorizontalNoEnterHelper
    ajax_commands = ['datatable', 'button']

    template_name = 'advanced_report_builder/extra_query_modal.html'
    no_header_x = True

    def __init__(self, *args, **kwargs):
        self._base_and_class = None
        super().__init__(*args, **kwargs)

    def post_save(self, created, form):
        self.add_command({'function': 'save_query_builder_id_extra_query'})
        return self.command_response('close')

    def form_setup(self, form, *_args, **_kwargs):
        fields = [
            'name',
            'target',
            FieldEx('query', template='advanced_report_builder/query_builder.html'),
            FieldEx('extra_query', template='advanced_report_builder/query_builder.html'),
        ]

        return fields

    def ajax_get_query_builder_fields(self, **kwargs):
        field_auto_id = kwargs['field_auto_id']
        report_type_id = self.slug['report_type']
        query_builder_filters = self.get_query_builder_report_type_field(report_type_id=report_type_id)
        return self.command_response(f'query_builder_{field_auto_id}', data=json.dumps(query_builder_filters))

    def get_report_builder_base_and_class(self):
        if self._base_and_class is None:
            self._base_and_class = self.get_report_builder_class(report_type_id=self.slug['report_type'])
        return self._base_and_class

    def get_report_type(self):
        return self.slug['report_type']

    def form_valid(self, form):
        org_id = self.object.pk if hasattr(self, 'object') else None
        instance = form.save(commit=False)
        instance._current_user = self.request.user
        instance.save()
        self.post_save(created=org_id is None, form=form)
        if not self.response_commands:
            self.add_command('reload')
        return self.command_response()
