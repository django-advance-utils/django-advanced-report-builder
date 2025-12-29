import json

from django.conf import settings
from django.forms import JSONField
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django_modals.modals import ModelFormModal
from django_modals.widgets.select2 import Select2

from advanced_report_builder.column_types import NUMBER_FIELDS
from advanced_report_builder.field_types import FieldTypes
from advanced_report_builder.field_utils import ReportBuilderFieldUtils
from advanced_report_builder.globals import FieldType
from advanced_report_builder.models import ReportQuery, ReportType
from advanced_report_builder.utils import get_report_builder_class


class QueryBuilderModalBaseMixin(ReportBuilderFieldUtils):
    @staticmethod
    def get_report_builder_class(report_type_id):
        if not report_type_id:
            return None, None

        report_type = get_object_or_404(ReportType, pk=report_type_id)
        base_model = report_type.content_type.model_class()
        report_builder_class = get_report_builder_class(model=base_model, report_type=report_type)
        return report_builder_class, base_model

    def get_query_builder_report_type_field(self, report_type_id):
        report_builder_class, base_model = self.get_report_builder_class(report_type_id=report_type_id)
        if report_builder_class is None:
            # noinspection PyUnresolvedReferences
            return self.command_response()
        query_builder_filters = []
        self._get_query_builder_fields(
            base_model=base_model,
            query_builder_filters=query_builder_filters,
            report_builder_class=report_builder_class,
        )

        return query_builder_filters

    def _get_query_builder_fields(
        self,
        base_model,
        query_builder_filters,
        report_builder_class,
    ):
        field_types = FieldTypes()
        field_results = []
        field_results_types = {
            FieldType.NULL_FIELD: {},
            FieldType.ABSTRACT_USER: {},
            FieldType.FILTER_FOREIGN_KEY: {},
            FieldType.STRING: {},
            FieldType.NUMBER: {},
            FieldType.BOOLEAN: {},
            FieldType.DATE: {},
            FieldType.MANY_TO_MANY: {},
        }
        field_types.get_field_types(
            field_results=field_results,
            field_results_types=field_results_types,
            base_model=base_model,
            report_builder_class=report_builder_class,
        )

        field_types.get_filters(
            fields=field_results, query_builder_filters=query_builder_filters, field_results_types=field_results_types
        )

    def ajax_get_fields(self, **kwargs):
        report_type_id = kwargs['report_type']
        report_builder_class, base_model = self.get_report_builder_class(report_type_id=report_type_id)
        fields = []
        tables = []
        self._get_fields(
            base_model=base_model,
            fields=fields,
            tables=tables,
            report_builder_class=report_builder_class,
            field_types=NUMBER_FIELDS,
            extra_fields=report_builder_class.extra_chart_field,
        )
        return self.command_response('report_fields', data=json.dumps({'fields': fields, 'tables': tables}))

    def get_fields_for_select2(self, field_type, report_type, search_string):
        fields = []
        if report_type != '':
            report_builder_fields, base_model = self.get_report_builder_class(report_type_id=report_type)
            fields = []
            if field_type == 'date':
                self._get_date_fields(
                    base_model=base_model,
                    fields=fields,
                    report_builder_class=report_builder_fields,
                    search_string=search_string,
                )
            elif field_type == 'number':
                self._get_number_fields(
                    base_model=base_model,
                    fields=fields,
                    report_builder_class=report_builder_fields,
                    search_string=search_string,
                )
            elif field_type == 'link':
                self._get_column_link_fields(
                    base_model=base_model,
                    fields=fields,
                    report_builder_class=report_builder_fields,
                    search_string=search_string,
                )
            elif field_type == 'colour':
                self._get_colour_fields(
                    base_model=base_model,
                    fields=fields,
                    report_builder_class=report_builder_fields,
                    search_string=search_string,
                )
            elif field_type == 'all':
                self._get_fields(
                    base_model=base_model,
                    fields=fields,
                    report_builder_class=report_builder_fields,
                    for_select2=True,
                    search_string=search_string,
                )
            elif field_type in ('order', 'django_order'):
                self._get_fields(
                    base_model=base_model,
                    fields=fields,
                    report_builder_class=report_builder_fields,
                    for_select2=True,
                    search_string=search_string,
                    show_order_by_fields=True,
                    must_have_django_field=field_type == 'django_order',
                )
            elif field_type == 'include_names':
                self._get_include_names(
                    base_model=base_model,
                    fields=fields,
                    report_builder_class=report_builder_fields,
                    search_string=search_string,
                )

        return JsonResponse({'results': fields})

    def setup_field(self, field_type, form, field_name, selected_field_id, report_type):
        _fields = []
        if selected_field_id:
            form.fields[field_name].initial = selected_field_id
            base_model = report_type.content_type.model_class()
            report_builder_class = get_report_builder_class(model=base_model, report_type=report_type)
            self.get_field_display_value(
                field_type=field_type,
                fields_values=_fields,
                base_model=base_model,
                report_builder_class=report_builder_class,
                selected_field_value=selected_field_id,
                for_select2=True,
            )

        form.fields[field_name].widget = Select2(attrs={'ajax': True})
        form.fields[field_name].widget.select_data = _fields


class QueryBuilderModalBase(QueryBuilderModalBaseMixin, ModelFormModal):
    size = 'xl'

    def __init__(self, *args, **kwargs):
        self.report_query = None
        self.show_query_name = False
        super().__init__(*args, **kwargs)

    def ajax_get_query_builder_fields(self, **kwargs):
        report_type_id = kwargs['report_type']

        field_auto_id = kwargs['field_auto_id']
        if report_type_id:
            query_builder_filters = self.get_query_builder_report_type_field(report_type_id=report_type_id)

            return self.command_response(f'query_builder_{field_auto_id}', data=json.dumps(query_builder_filters))
        else:
            return self.command_response()

    def add_query_data(self, form):
        form.fields['extra_query_data'] = JSONField(required=False, label='Numerator filter')
        if self.object.id:
            query_id = self.slug.get('query_id')
            if query_id:
                self.report_query = get_object_or_404(ReportQuery, id=query_id)
            else:
                self.report_query = self.object.reportquery_set.first()
            if self.report_query:
                form.fields['extra_query_data'].initial = self.report_query.extra_query

    def form_valid(self, form):
        org_id = self.object.id if hasattr(self, 'object') else None
        chart_report = form.save(commit=False)
        chart_report._current_user = self.request.user
        chart_report.save()
        form.save_m2m()

        self.post_save(created=org_id is None, form=form)
        if not self.response_commands:
            url_name = getattr(settings, 'REPORT_BUILDER_DETAIL_URL_NAME', '')
            if org_id is None and url_name:
                url = reverse(url_name, kwargs={'slug': chart_report.slug})
                self.add_command('redirect', url=url)
            else:
                self.add_command('reload')
        return self.command_response()
