import json
import logging

from django.conf import settings

from advanced_report_builder.field_utils import ReportBuilderFieldUtils
from advanced_report_builder.utils import get_report_builder_class

logger = logging.getLogger(__name__)


def is_available():
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    return bool(getattr(settings, 'ANTHROPIC_API_KEY', ''))


def build_field_schema(report_type):
    base_model = report_type.content_type.model_class()
    report_builder_class = get_report_builder_class(model=base_model, report_type=report_type)
    if report_builder_class is None:
        return []

    field_utils = ReportBuilderFieldUtils()
    fields = []
    field_utils._get_fields(
        base_model=base_model,
        fields=fields,
        report_builder_class=report_builder_class,
        for_select2=True,
    )

    field_types_helper = _FieldTypeHelper()
    field_type_map = field_types_helper.get_field_type_map(
        base_model=base_model,
        report_builder_class=report_builder_class,
    )

    schema = []
    for field in fields:
        field_id = field['id']
        field_type = field_type_map.get(field_id, 'string')
        schema.append({
            'field_id': field_id,
            'label': field['text'],
            'type': field_type,
        })
    return schema


class _FieldTypeHelper(ReportBuilderFieldUtils):
    def get_field_type_map(self, base_model, report_builder_class):
        from advanced_report_builder.column_types import BOOLEAN_FIELD, DATE_FIELDS, NUMBER_FIELDS

        field_type_map = {}
        for report_builder_field in report_builder_class.fields:
            if not isinstance(report_builder_field, str) or report_builder_field not in report_builder_class.exclude_display_fields:
                try:
                    django_field, col_type_override, columns, _ = self.get_field_details(
                        base_model=base_model,
                        field=report_builder_field,
                        report_builder_class=report_builder_class,
                    )
                except Exception:
                    continue

                for column in columns:
                    field_id = column.column_name
                    if django_field is not None:
                        if isinstance(django_field, DATE_FIELDS):
                            field_type_map[field_id] = 'date'
                        elif isinstance(django_field, NUMBER_FIELDS):
                            field_type_map[field_id] = 'number'
                        elif isinstance(django_field, BOOLEAN_FIELD):
                            field_type_map[field_id] = 'boolean'
                        else:
                            field_type_map[field_id] = 'string'

        # Recurse into includes
        for include_field, include in report_builder_class.includes.items():
            from django.apps import apps
            app_label, model, rb_class_str = include['model'].split('.')
            new_model = apps.get_model(app_label, model)
            new_rb_class = get_report_builder_class(model=new_model, class_name=rb_class_str)
            if new_rb_class is not None:
                sub_map = self.get_field_type_map(
                    base_model=new_model,
                    report_builder_class=new_rb_class,
                )
                for sub_field_id, sub_type in sub_map.items():
                    field_type_map[f'{include_field}__{sub_field_id}'] = sub_type

        return field_type_map


OUTPUT_TYPE_SCHEMAS = {
    'table': '''{
  "name": "Report name",
  "table_fields": [{"field": "field_id_1"}, {"field": "field_id_2"}],
  "order_by_field": "field_id or null",
  "order_by_ascending": true,
  "page_length": 100,
  "filters": null
}

table_fields is a JSON list of objects with a "field" key.''',

    'bar_chart': '''{
  "name": "Report name",
  "axis_scale": 3,
  "date_field": "field_id of a date field",
  "axis_value_type": 4,
  "fields": [{"field": "field_id_1"}],
  "x_label": "X axis label or null",
  "y_label": "Y axis label or null",
  "stacked": false,
  "show_totals": false,
  "filters": null
}

axis_scale: 1=Year, 2=Quarter, 3=Month, 4=Week, 5=Day
axis_value_type: 1=Sum, 2=Maximum, 3=Minimum, 4=Count, 5=Average
fields is a JSON list of objects with a "field" key (the fields to aggregate/group by).''',

    'line_chart': '''{
  "name": "Report name",
  "axis_scale": 3,
  "date_field": "field_id of a date field",
  "axis_value_type": 4,
  "fields": [{"field": "field_id_1"}],
  "x_label": "X axis label or null",
  "y_label": "Y axis label or null",
  "show_totals": false,
  "filters": null
}

axis_scale: 1=Year, 2=Quarter, 3=Month, 4=Week, 5=Day
axis_value_type: 1=Sum, 2=Maximum, 3=Minimum, 4=Count, 5=Average
fields is a JSON list of objects with a "field" key.''',

    'pie_chart': '''{
  "name": "Report name",
  "axis_value_type": 4,
  "fields": [{"field": "field_id_1"}],
  "style": 1,
  "filters": null
}

axis_value_type: 1=Sum, 2=Maximum, 3=Minimum, 4=Count, 5=Average
style: 1=Pie, 2=Doughnut
fields is a JSON list of objects with a "field" key.''',

    'single_value': '''{
  "name": "Report name",
  "single_value_type": 1,
  "field": "field_id or null",
  "prefix": "optional prefix like $ or null",
  "decimal_places": 0,
  "filters": null
}

single_value_type: 1=Count, 2=Sum, 3=Count & Sum, 4=Percent, 5=Percent from Count, 6=Average Sum from Count
field is required for Sum/Percent/Average types (must be a number field).''',

    'funnel_chart': '''{
  "name": "Report name",
  "axis_value_type": 4,
  "fields": [{"field": "field_id_1"}],
  "filters": null
}

axis_value_type: 1=Sum, 2=Maximum, 3=Minimum, 4=Count, 5=Average
fields is a JSON list of objects with a "field" key.''',
}


def build_system_prompt(report_type, field_schema, output_type):
    fields_json = json.dumps(field_schema, indent=2)
    schema = OUTPUT_TYPE_SCHEMAS.get(output_type, OUTPUT_TYPE_SCHEMAS['table'])

    return f"""You are a report configuration assistant. Given a user's natural language description and available data fields, generate a JSON report configuration.

## Available Data Fields

The data source is: "{report_type.name}"

Available fields:
{fields_json}

Each field has:
- "field_id": The internal field path (use ONLY these exact values)
- "label": Human-readable name
- "type": One of "string", "number", "date", "boolean"

## Output Type: {output_type}

## Response Format

Return ONLY valid JSON matching this schema (no markdown, no explanation):

{schema}

## Filter Format

If the user describes filtering criteria, generate filters in this format:
{{
  "condition": "AND",
  "rules": [
    {{
      "id": "field_id",
      "field": "field_id",
      "type": "string",
      "operator": "contains",
      "value": "the value"
    }}
  ]
}}

String operators: equal, not_equal, contains, not_contains, begins_with, ends_with
Number operators: equal, not_equal, less, less_or_equal, greater, greater_or_equal
Date operators: equal, not_equal, less, less_or_equal, greater, greater_or_equal, is_null, is_not_null
Boolean operators: equal, not_equal (values: "1" for True, "0" for False)

For date filters use the variable date approach: set the id to "field_id__variable_date" and use values like "variable_date:7" for This Year, "variable_date:8" for Last Year, "variable_date:5" for This Month, "variable_date:6" for Last Month, "variable_date:1" for Today, "variable_date:2" for Yesterday.

## Important Rules
- ONLY use field_ids from the Available Data Fields list above
- Return ONLY the JSON object, no surrounding text or markdown
- Pick sensible defaults for any fields not specified by the user"""


def call_llm(system_prompt, user_prompt):
    import anthropic

    api_key = getattr(settings, 'ANTHROPIC_API_KEY', '')
    model = getattr(settings, 'REPORT_BUILDER_NL_MODEL', 'claude-sonnet-4-20250514')
    max_tokens = getattr(settings, 'REPORT_BUILDER_NL_MAX_TOKENS', 2048)

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[
            {'role': 'user', 'content': user_prompt},
        ],
    )

    response_text = message.content[0].text.strip()

    # Strip markdown code fences if present
    if response_text.startswith('```'):
        lines = response_text.split('\n')
        lines = lines[1:]  # Remove opening ```json or ```
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
        response_text = '\n'.join(lines)

    return json.loads(response_text)
