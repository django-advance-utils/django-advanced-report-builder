import json

from crispy_forms.bootstrap import StrictButton
from django.apps import apps
from django.forms import CharField
from django.shortcuts import get_object_or_404
from django_datatables.datatables import ColumnInitialisor
from django_modals.forms import ModelCrispyForm
from django_modals.modals import ModelFormModal

from advanced_report_builder.field_types import FieldTypes
from advanced_report_builder.models import ReportQuery, ReportType


class QueryBuilderModelForm(ModelCrispyForm):
    def submit_button(self, css_class='btn-success modal-submit', button_text='Submit', **kwargs):
        return StrictButton(button_text, onclick=f'save_modal_{ self.form_id }()', css_class=css_class, **kwargs)


class QueryBuilderModalBaseMixin:

    def get_query_builder_report_type_field(self, report_type_id):
        if not report_type_id:
            return self.command_response()
        report_type = get_object_or_404(ReportType, pk=report_type_id)
        base_model = report_type.content_type.model_class()
        report_builder_fields = getattr(base_model, report_type.report_builder_class_name, None)
        query_builder_filters = []
        self._get_query_builder_fields(base_model=base_model,
                                       query_builder_filters=query_builder_filters,
                                       report_builder_fields=report_builder_fields)

        return query_builder_filters

    def _get_query_builder_fields(self, base_model, query_builder_filters, report_builder_fields, prefix='',
                                  title_prefix=''):

        field_types = FieldTypes()

        for report_builder_field in report_builder_fields.fields:

            column_initialisor = ColumnInitialisor(start_model=base_model, path=report_builder_field)
            columns = column_initialisor.get_columns()
            for column in columns:
                if column_initialisor.django_field is not None:
                    field_types.get_filter(query_builder_filters=query_builder_filters,
                                           django_field=column_initialisor.django_field,
                                           field=prefix + column.column_name,
                                           title=title_prefix + column.title)
        for include in report_builder_fields.includes:
            app_label, model, report_builder_fields_str = include['model'].split('.')
            new_model = apps.get_model(app_label, model)
            new_report_builder_fields = getattr(new_model, report_builder_fields_str, None)
            foreign_key_field = getattr(base_model, include['field'], None).field
            if foreign_key_field.null:
                field_types.get_foreign_key_null_field(query_builder_filters=query_builder_filters,
                                                       field=prefix + include['field'],
                                                       title=title_prefix + include['title'])

            self._get_query_builder_fields(base_model=new_model,
                                           query_builder_filters=query_builder_filters,
                                           report_builder_fields=new_report_builder_fields,
                                           prefix=f"{include['field']}__",
                                           title_prefix=f"{include['title']} --> ")


class QueryBuilderModalBase(QueryBuilderModalBaseMixin, ModelFormModal):
    base_form = QueryBuilderModelForm
    size = 'xl'

    def __init__(self, *args, **kwargs):
        self.report_query = None
        self.show_query_name = False
        super().__init__(*args, **kwargs)

    def ajax_get_query_builder_fields(self, **kwargs):
        report_type_id = kwargs['report_type'][0]
        field_auto_id = kwargs['field_auto_id'][0]
        if report_type_id:
            query_builder_filters = self.get_query_builder_report_type_field(report_type_id=report_type_id)

            return self.command_response(f'query_builder_{field_auto_id}', data=json.dumps(query_builder_filters))
        else:
            return self.command_response(f'query_builder_{field_auto_id}', data='[]')

    def add_query_data(self, form, include_extra_query=True):
        form.fields['query_data'] = CharField(required=False, label='Filter')

        if include_extra_query:
            form.fields['extra_query_data'] = CharField(required=False, label='Numerator filter')

        if self.object.id:
            query_id = self.slug.get('query_id')
            if query_id:
                self.report_query = get_object_or_404(ReportQuery, id=query_id)
            else:
                self.report_query = self.object.reportquery_set.first()

            if self.report_query:
                self.show_query_name = self.object.reportquery_set.count() > 1
                if self.show_query_name:
                    form.fields['query_data'] = CharField(required=True, initial=self.report_query.name)

                form.fields['query_data'].initial = self.report_query.query
                if include_extra_query:
                    form.fields['extra_query_data'].initial = self.report_query.extra_query
