import json
import logging

from django.conf import settings
from django.forms import CharField, ChoiceField, Textarea
from django.http import Http404
from django.urls import reverse
from django_modals.forms import CrispyForm
from django_modals.helper import modal_button, modal_button_method
from django_modals.modals import FormModal, Modal
from django_modals.widgets.select2 import Select2

from advanced_report_builder.models import ReportType
from advanced_report_builder.nl_prompt import (
    build_field_schema,
    build_system_prompt,
    call_llm,
    is_available,
)
from advanced_report_builder.nl_report_factory import NLReportFactory

logger = logging.getLogger(__name__)

OUTPUT_TYPE_CHOICES = [
    ('table', 'Table'),
    ('bar_chart', 'Bar Chart'),
    ('line_chart', 'Line Chart'),
    ('pie_chart', 'Pie Chart'),
    ('single_value', 'Single Value'),
    ('funnel_chart', 'Funnel Chart'),
]

EDIT_MODAL_MAP = {
    'tablereport': 'advanced_report_builder:table_modal',
    'barchartreport': 'advanced_report_builder:bar_chart_modal',
    'linechartreport': 'advanced_report_builder:line_chart_modal',
    'piechartreport': 'advanced_report_builder:pie_chart_modal',
    'singlevaluereport': 'advanced_report_builder:single_value_modal',
    'funnelchartreport': 'advanced_report_builder:funnel_chart_modal',
}


class NLReportBuilderModal(FormModal):
    form_class = CrispyForm
    modal_title = 'Build Report with AI'
    template_name = 'advanced_report_builder/nl_builder/prompt_modal.html'

    def dispatch(self, request, *args, **kwargs):
        if not is_available():
            raise Http404('Natural language report builder is not available.')
        return super().dispatch(request, *args, **kwargs)

    def form_setup(self, form, *_args, **_kwargs):
        report_type_choices = [(rt.pk, rt.name) for rt in ReportType.objects.all()]
        form.fields['report_type'] = ChoiceField(
            choices=report_type_choices,
            widget=Select2,
            label='Data Source',
        )
        form.fields['output_type'] = ChoiceField(
            choices=OUTPUT_TYPE_CHOICES,
            widget=Select2,
            label='Output Type',
        )
        form.fields['description'] = CharField(
            widget=Textarea(attrs={'rows': 4, 'placeholder': 'e.g. Show me all active companies with their name, sector and creation date'}),
            label='Describe what you want',
        )

    def form_valid(self, form):
        report_type_id = form.cleaned_data['report_type']
        output_type = form.cleaned_data['output_type']
        description = form.cleaned_data['description']

        try:
            report_type = ReportType.objects.get(pk=report_type_id)
        except ReportType.DoesNotExist:
            form.add_error('report_type', 'Invalid data source selected.')
            return self.form_invalid(form)

        try:
            field_schema = build_field_schema(report_type)
            system_prompt = build_system_prompt(report_type, field_schema, output_type)
            config = call_llm(system_prompt, description)
        except json.JSONDecodeError:
            form.add_error(None, 'The AI returned an invalid response. Please try again with a different description.')
            return self.form_invalid(form)
        except Exception as e:
            logger.exception('NL Report Builder LLM error')
            form.add_error(None, f'Error generating report: {e}')
            return self.form_invalid(form)

        # Store config in session for preview modal
        self.request.session['nl_report_config'] = json.dumps(config)
        self.request.session['nl_report_type_id'] = report_type_id
        self.request.session['nl_output_type'] = output_type
        self.request.session['nl_description'] = description

        slug = f'preview-1'
        return self.command_response(
            'show_modal',
            modal=reverse('advanced_report_builder:nl_builder_preview_modal', kwargs={'slug': slug}),
        )


class NLReportPreviewModal(Modal):
    modal_title = 'Preview AI Generated Report'
    template_name = 'advanced_report_builder/nl_builder/preview_modal.html'

    def dispatch(self, request, *args, **kwargs):
        if not is_available():
            raise Http404('Natural language report builder is not available.')
        return super().dispatch(request, *args, **kwargs)

    def _get_session_data(self):
        config_json = self.request.session.get('nl_report_config')
        if not config_json:
            return None, None, None
        config = json.loads(config_json)
        report_type_id = self.request.session.get('nl_report_type_id')
        output_type = self.request.session.get('nl_output_type')
        return config, report_type_id, output_type

    def modal_content(self):
        config, report_type_id, output_type = self._get_session_data()
        if config is None:
            return '<p>No report configuration found. Please go back and try again.</p>'

        output_type_label = dict(OUTPUT_TYPE_CHOICES).get(output_type, output_type)

        try:
            report_type = ReportType.objects.get(pk=report_type_id)
            data_source = report_type.name
        except ReportType.DoesNotExist:
            data_source = 'Unknown'

        lines = [
            f'<h5>{config.get("name", "Untitled Report")}</h5>',
            f'<p><strong>Type:</strong> {output_type_label}</p>',
            f'<p><strong>Data Source:</strong> {data_source}</p>',
        ]

        # Show type-specific details
        if output_type == 'table':
            fields = config.get('table_fields', [])
            if fields:
                field_list = ', '.join(f if isinstance(f, str) else f.get('field', '') for f in fields)
                lines.append(f'<p><strong>Fields:</strong> {field_list}</p>')
            order = config.get('order_by_field')
            if order:
                direction = 'ascending' if config.get('order_by_ascending', True) else 'descending'
                lines.append(f'<p><strong>Order by:</strong> {order} ({direction})</p>')

        elif output_type in ('bar_chart', 'line_chart'):
            scale_map = {1: 'Year', 2: 'Quarter', 3: 'Month', 4: 'Week', 5: 'Day'}
            value_map = {1: 'Sum', 2: 'Maximum', 3: 'Minimum', 4: 'Count', 5: 'Average'}
            lines.append(f'<p><strong>Date Field:</strong> {config.get("date_field", "N/A")}</p>')
            lines.append(f'<p><strong>Scale:</strong> {scale_map.get(config.get("axis_scale"), "N/A")}</p>')
            lines.append(f'<p><strong>Value Type:</strong> {value_map.get(config.get("axis_value_type"), "N/A")}</p>')
            fields = config.get('fields', [])
            if fields:
                field_list = ', '.join(f if isinstance(f, str) else f.get('field', '') for f in fields)
                lines.append(f'<p><strong>Fields:</strong> {field_list}</p>')

        elif output_type == 'pie_chart':
            value_map = {1: 'Sum', 2: 'Maximum', 3: 'Minimum', 4: 'Count', 5: 'Average'}
            style_map = {1: 'Pie', 2: 'Doughnut'}
            lines.append(f'<p><strong>Value Type:</strong> {value_map.get(config.get("axis_value_type"), "N/A")}</p>')
            lines.append(f'<p><strong>Style:</strong> {style_map.get(config.get("style"), "N/A")}</p>')
            fields = config.get('fields', [])
            if fields:
                field_list = ', '.join(f if isinstance(f, str) else f.get('field', '') for f in fields)
                lines.append(f'<p><strong>Fields:</strong> {field_list}</p>')

        elif output_type == 'single_value':
            sv_map = {1: 'Count', 2: 'Sum', 3: 'Count & Sum', 4: 'Percent', 5: 'Percent from Count', 6: 'Average'}
            lines.append(f'<p><strong>Value Type:</strong> {sv_map.get(config.get("single_value_type"), "N/A")}</p>')
            field = config.get('field')
            if field:
                lines.append(f'<p><strong>Field:</strong> {field}</p>')

        elif output_type == 'funnel_chart':
            value_map = {1: 'Sum', 2: 'Maximum', 3: 'Minimum', 4: 'Count', 5: 'Average'}
            lines.append(f'<p><strong>Value Type:</strong> {value_map.get(config.get("axis_value_type"), "N/A")}</p>')
            fields = config.get('fields', [])
            if fields:
                field_list = ', '.join(f if isinstance(f, str) else f.get('field', '') for f in fields)
                lines.append(f'<p><strong>Fields:</strong> {field_list}</p>')

        # Show filters
        filters = config.get('filters')
        if filters and filters.get('rules'):
            filter_lines = []
            for rule in filters['rules']:
                filter_lines.append(f'{rule.get("field", "?")} {rule.get("operator", "?")} {rule.get("value", "")}')
            lines.append(f'<p><strong>Filters:</strong> {"; ".join(filter_lines)}</p>')

        return '\n'.join(lines)

    def get_modal_buttons(self):
        return [
            modal_button_method('Create Report', 'create_report', 'btn-success'),
            modal_button_method('Back', 'back', 'btn-secondary'),
            modal_button('Cancel', 'close', 'btn-secondary'),
        ]

    def button_create_report(self, **_kwargs):
        config, report_type_id, output_type = self._get_session_data()
        if config is None:
            return self.command_response('close')

        try:
            report_type = ReportType.objects.get(pk=report_type_id)
        except ReportType.DoesNotExist:
            return self.command_response('close')

        user = self.request.user if self.request.user.is_authenticated else None
        factory = NLReportFactory()
        report = factory.create_report(config, report_type, output_type, user=user)

        # Clean up session
        for key in ('nl_report_config', 'nl_report_type_id', 'nl_output_type', 'nl_description'):
            self.request.session.pop(key, None)

        # Redirect to report edit modal or detail page
        edit_modal_name = EDIT_MODAL_MAP.get(report.instance_type)
        if edit_modal_name:
            url = reverse(edit_modal_name, kwargs={'slug': f'pk-{report.pk}'})
            return self.command_response('show_modal', modal=url)

        url_name = getattr(settings, 'REPORT_BUILDER_DETAIL_URL_NAME', '')
        if url_name:
            url = reverse(url_name, kwargs={'slug': report.slug})
            return self.command_response('redirect', url=url)

        return self.command_response('reload')

    def button_back(self, **_kwargs):
        url = reverse('advanced_report_builder:nl_builder_prompt_modal', kwargs={'slug': 'new-1'})
        return self.command_response('show_modal', modal=url)
