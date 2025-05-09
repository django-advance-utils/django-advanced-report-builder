import base64
import json

from crispy_forms.layout import Div
from django.forms import BooleanField, CharField, ChoiceField
from django.urls import reverse
from django_menus.menu import MenuItem
from django_modals.fields import FieldEx
from django_modals.form_helpers import HorizontalNoEnterHelper
from django_modals.modals import FormModal
from django_modals.processes import PERMISSION_OFF, PROCESS_EDIT_DELETE
from django_modals.widgets.colour_picker import ColourPickerWidget
from django_modals.widgets.select2 import Select2Multiple

from advanced_report_builder.models import FunnelChartReport
from advanced_report_builder.toggle import RBToggle
from advanced_report_builder.utils import (
    decode_attribute,
    encode_attribute,
    get_report_builder_class,
    split_attr,
)
from advanced_report_builder.views.charts_base import ChartBaseFieldForm, ChartBaseView
from advanced_report_builder.views.modals_base import (
    QueryBuilderModalBase,
    QueryBuilderModalBaseMixin,
)
from advanced_report_builder.views.query_modal.mixin import MultiQueryModalMixin


class FunnelChartView(ChartBaseView):
    use_annotations = False

    template_name = 'advanced_report_builder/charts/funnel/report.html'

    def dispatch(self, request, *args, **kwargs):
        self.report = kwargs.get('report')
        self.chart_report = self.report.funnelchartreport
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.table.funnel_chart_report = self.chart_report
        self.table.datatable_template = 'advanced_report_builder/charts/funnel/middle.html'
        context['funnel_chart_report'] = self.chart_report
        return context

    def set_extra_number_field_kwargs(self, data_attr, options, multiple_index, additional_options):
        funnel_colour = None
        if additional_options is not None:
            funnel_colour = additional_options.get('positive_colour')
        if funnel_colour is None or funnel_colour == '':
            funnel_colour = data_attr.get('funnel_colour') or '801C70'
            funnel_colour = self.add_colour_offset(funnel_colour, multiple_index=multiple_index)
        options.update({'colour': funnel_colour})

    def edit_report_menu(self, request, chart_report_id, slug_str):
        return [
            MenuItem(
                f'advanced_report_builder:funnel_chart_modal,pk-{chart_report_id}{slug_str}',
                menu_display='Edit',
                font_awesome='fas fa-pencil-alt',
                css_classes=['btn-primary'],
            ),
            *self.duplicate_menu(request=self.request, report_id=chart_report_id),
        ]

    def get_date_field(self, index, fields, base_model, table):
        return None


class FunnelChartModal(MultiQueryModalMixin, QueryBuilderModalBase):
    template_name = 'advanced_report_builder/charts/modal.html'
    process = PROCESS_EDIT_DELETE
    permission_delete = PERMISSION_OFF
    model = FunnelChartReport
    widgets = {'report_tags': Select2Multiple}
    show_order_by = False

    form_fields = [
        'name',
        'notes',
        'report_type',
        'report_tags',
        'axis_value_type',
        'fields',
    ]

    def form_setup(self, form, *_args, **_kwargs):
        url = reverse(
            'advanced_report_builder:funnel_chart_field_modal',
            kwargs={'slug': 'selector-99999-data-FIELD_INFO-report_type_id-REPORT_TYPE_ID'},
        )

        fields = [
            'name',
            'notes',
            'report_type',
            'report_tags',
            'axis_value_type',
            FieldEx(
                'fields',
                template='advanced_report_builder/select_column.html',
                extra_context={'select_column_url': url, 'command_prefix': ''},
            ),
            FieldEx('query_data', template='advanced_report_builder/query_builder.html'),
        ]
        if self.object.id:
            self.add_extra_queries(form=form, fields=fields)
        return fields


class FunnelChartFieldForm(ChartBaseFieldForm):
    def setup_modal(self, *args, **kwargs):
        data = json.loads(base64.b64decode(self.slug['data']))
        report_type, base_model = self.get_report_type_details()

        data_attr = split_attr(data)

        self.fields['title'] = CharField(initial=data['title'])

        self.fields['funnel_colour'] = CharField(required=False, widget=ColourPickerWidget)
        self.fields['funnel_colour'].initial = data_attr.get('funnel_colour')

        self.fields['has_filter'] = BooleanField(required=False, widget=RBToggle())
        self.fields['filter'] = CharField(required=False)

        if data_attr.get('has_filter') == '1':
            self.fields['has_filter'].initial = True
            if 'filter' in data_attr:
                self.fields['filter'].initial = decode_attribute(data_attr['filter'])

        self.fields['multiple_columns'] = BooleanField(required=False, widget=RBToggle())
        self.fields['append_column_title'] = BooleanField(required=False, widget=RBToggle())

        report_builder_class = get_report_builder_class(model=base_model, report_type=report_type)
        self.setup_colour_field(
            form_fields=self.fields,
            base_model=base_model,
            report_builder_class=report_builder_class,
            name='positive_colour_field',
            data_attr=data_attr,
            label='Funnel colour field',
        )

        multiple_column_field = []
        self._get_query_builder_foreign_key_fields(
            base_model=base_model,
            report_builder_class=report_builder_class,
            fields=multiple_column_field,
        )

        self.fields['multiple_column_field'] = ChoiceField(choices=multiple_column_field, required=False)
        if data_attr.get('multiple_columns') == '1':
            self.fields['multiple_columns'].initial = True
            self.fields['multiple_column_field'].initial = data_attr.get('multiple_column_field')
            if data_attr.get('append_column_title') == '1':
                self.fields['append_column_title'].initial = True

        super().setup_modal(*args, **kwargs)

    def get_additional_attributes(self):
        attributes = []
        self.get_report_type_details()

        attributes.append(f'funnel_colour-{self.cleaned_data["funnel_colour"]}')

        if self.cleaned_data['has_filter']:
            attributes.append('has_filter-1')

            if self.cleaned_data['filter']:
                b64_filter = encode_attribute(self.cleaned_data['filter'])
                attributes.append(f'filter-{b64_filter}')
            if self.cleaned_data['multiple_columns']:
                attributes.append('multiple_columns-1')
                if self.cleaned_data['positive_colour_field']:
                    attributes.append(f'positive_colour_field-{self.cleaned_data["positive_colour_field"]}')
                attributes.append(f'multiple_column_field-{self.cleaned_data["multiple_column_field"]}')
                if self.cleaned_data['append_column_title']:
                    attributes.append('append_column_title-1')

        if attributes:
            return '-'.join(attributes)
        return None


class FunnelChartFieldModal(QueryBuilderModalBaseMixin, FormModal):
    form_class = FunnelChartFieldForm
    size = 'xl'
    template_name = 'advanced_report_builder/charts/modal_field.html'
    no_header_x = True
    helper_class = HorizontalNoEnterHelper

    @property
    def modal_title(self):
        data = json.loads(base64.b64decode(self.slug['data']))
        return f'Edit {data["title"]}'

    def form_valid(self, form):
        selector = self.slug['selector']

        _attr = form.get_additional_attributes()
        self.add_command(
            {
                'function': 'set_attr',
                'selector': f'#{selector}',
                'attr': 'data-attr',
                'val': _attr,
            }
        )

        self.add_command(
            {
                'function': 'html',
                'selector': f'#{selector} span',
                'html': form.cleaned_data['title'],
            }
        )
        self.add_command({'function': 'update_selection'})
        return self.command_response('close')

    # noinspection PyMethodMayBeStatic
    def form_setup(self, form, *_args, **_kwargs):
        form.add_trigger(
            'has_filter',
            'onchange',
            [
                {
                    'selector': '#filter_fields_div',
                    'values': {'checked': 'show'},
                    'default': 'hide',
                }
            ],
        )

        form.add_trigger(
            'multiple_columns',
            'onchange',
            [
                {
                    'selector': '#multiple_columns_fields_div',
                    'values': {'checked': 'show'},
                    'default': 'hide',
                },
            ],
        )

        return [
            'title',
            'funnel_colour',
            Div(
                FieldEx(
                    'has_filter',
                    template='django_modals/fields/label_checkbox.html',
                    field_class='col-6 input-group-sm',
                ),
                Div(
                    FieldEx(
                        'filter',
                        template='advanced_report_builder/datatables/fields/single_query_builder.html',
                    ),
                    FieldEx(
                        'multiple_columns',
                        template='django_modals/fields/label_checkbox.html',
                        field_class='col-6 input-group-sm',
                    ),
                    Div(
                        FieldEx(
                            'append_column_title',
                            template='django_modals/fields/label_checkbox.html',
                            field_class='col-6 input-group-sm',
                        ),
                        FieldEx('multiple_column_field'),
                        FieldEx('positive_colour_field'),
                        css_id='multiple_columns_fields_div',
                    ),
                    css_id='filter_fields_div',
                ),
                css_id='annotations_fields_div',
            ),
        ]

    def ajax_get_query_builder_fields(self, **kwargs):
        field_auto_id = kwargs['field_auto_id']

        report_type_id = self.slug['report_type_id']
        query_builder_filters = self.get_query_builder_report_type_field(report_type_id=report_type_id)

        return self.command_response(f'query_builder_{field_auto_id}', data=json.dumps(query_builder_filters))
