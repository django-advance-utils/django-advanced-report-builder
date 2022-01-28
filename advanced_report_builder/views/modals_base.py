import json

from crispy_forms.bootstrap import StrictButton
from django.apps import apps
from django.forms import CharField
from django.shortcuts import get_object_or_404
from django_datatables.datatables import ColumnInitialisor
from django_modals.forms import ModelCrispyForm
from django_modals.modals import ModelFormModal

from advanced_report_builder.field_types import FieldTypes
from advanced_report_builder.globals import DATE_FIELDS, NUMBER_FIELDS
from advanced_report_builder.models import ReportQuery, ReportType
from advanced_report_builder.utils import get_django_field


class QueryBuilderModelForm(ModelCrispyForm):
    def submit_button(self, css_class='btn-success modal-submit', button_text='Submit', **kwargs):
        return StrictButton(button_text, onclick=f'save_modal_{ self.form_id }()', css_class=css_class, **kwargs)


class QueryBuilderModalBaseMixin:

    @staticmethod
    def get_report_builder_fields(report_type_id):
        if not report_type_id:
            return None, None

        report_type = get_object_or_404(ReportType, pk=report_type_id)
        base_model = report_type.content_type.model_class()
        report_builder_fields = getattr(base_model, report_type.report_builder_class_name, None)
        return report_builder_fields, base_model

    def get_query_builder_report_type_field(self, report_type_id):

        report_builder_fields, base_model = self.get_report_builder_fields(report_type_id=report_type_id)
        if report_builder_fields is None:
            # noinspection PyUnresolvedReferences
            return self.command_response()
        query_builder_filters = []
        self._get_query_builder_fields(base_model=base_model,
                                       query_builder_filters=query_builder_filters,
                                       report_builder_fields=report_builder_fields)

        return query_builder_filters

    def _get_query_builder_fields(self, base_model, query_builder_filters, report_builder_fields, prefix='',
                                  title_prefix='', previous_base_model=None):

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

            if new_model != previous_base_model:
                _foreign_key = getattr(base_model, include['field'], None)

                if hasattr(_foreign_key, 'field'):
                    add_null_field = _foreign_key.field.null
                else:
                    add_null_field = True

                if add_null_field:
                    field_types.get_foreign_key_null_field(query_builder_filters=query_builder_filters,
                                                           field=prefix + include['field'],
                                                           title=title_prefix + include['title'])

                self._get_query_builder_fields(base_model=new_model,
                                               query_builder_filters=query_builder_filters,
                                               report_builder_fields=new_report_builder_fields,
                                               prefix=f"{prefix}{include['field']}__",
                                               title_prefix=f"{include['title']} --> ",
                                               previous_base_model=base_model)


class QueryBuilderModalBase(QueryBuilderModalBaseMixin, ModelFormModal):
    base_form = QueryBuilderModelForm
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

    def _get_fields(self, base_model, fields, tables, report_builder_fields,
                    prefix='', title_prefix='', title=None, colour=None,
                    previous_base_model=None, selected_field_id=None, for_select2=False,
                    all_fields=False, pivot_fields=None):
        if title is None:
            title = report_builder_fields.title
        if colour is None:
            colour = report_builder_fields.colour

        tables.append({'name': title,
                       'colour': colour})

        for report_builder_field in report_builder_fields.fields:
            django_field, col_type_override, columns = get_django_field(base_model=base_model,
                                                                        field=report_builder_field)
            for column in columns:
                if all_fields or isinstance(django_field, NUMBER_FIELDS) or column.annotations:
                    full_id = prefix + column.column_name
                    if selected_field_id is None or selected_field_id == full_id:
                        if for_select2:
                            fields.append({'id': full_id,
                                           'text': title_prefix + column.title})
                        else:
                            fields.append({'field': full_id,
                                           'label': title_prefix + column.title,
                                           'colour': report_builder_fields.colour})

        if not for_select2 and pivot_fields is not None:
            for pivot_field in report_builder_fields.pivot_fields:
                full_id = prefix + pivot_field['field']
                pivot_fields.append({'field': full_id,
                                     'label': title_prefix + pivot_field['title'],
                                     'colour': report_builder_fields.colour})

        for include in report_builder_fields.includes:
            app_label, model, report_builder_fields_str = include['model'].split('.')

            new_model = apps.get_model(app_label, model)
            if new_model != previous_base_model:
                new_report_builder_fields = getattr(new_model, report_builder_fields_str, None)
                self._get_fields(base_model=new_model,
                                 fields=fields,
                                 tables=tables,
                                 report_builder_fields=new_report_builder_fields,
                                 prefix=f"{prefix}{include['field']}__",
                                 title_prefix=f"{title_prefix}{include['title']} -> ",
                                 title=include.get('title'),
                                 colour=include.get('colour'),
                                 previous_base_model=base_model,
                                 selected_field_id=selected_field_id,
                                 for_select2=for_select2,
                                 all_fields=all_fields,
                                 pivot_fields=pivot_fields)

    def ajax_get_fields(self, **kwargs):
        report_type_id = kwargs['report_type']
        report_builder_fields, base_model = self.get_report_builder_fields(report_type_id=report_type_id)
        fields = []
        tables = []
        self._get_fields(base_model=base_model,
                         fields=fields,
                         tables=tables,
                         report_builder_fields=report_builder_fields)
        return self.command_response('report_fields', data=json.dumps({'fields': fields, 'tables': tables}))

    def _get_date_fields(self, base_model, fields, report_builder_fields,
                         prefix='', title_prefix='', selected_field_id=None, previous_base_model=None):

        for report_builder_field in report_builder_fields.fields:
            django_field, _, columns = get_django_field(base_model=base_model, field=report_builder_field)
            for column in columns:
                if isinstance(django_field, DATE_FIELDS):
                    full_id = prefix + column.column_name
                    if selected_field_id is None or selected_field_id == full_id:
                        fields.append({'id': full_id,
                                       'text': title_prefix + column.title})

        for include in report_builder_fields.includes:
            app_label, model, report_builder_fields_str = include['model'].split('.')
            new_model = apps.get_model(app_label, model)
            if new_model != previous_base_model:
                new_report_builder_fields = getattr(new_model, report_builder_fields_str, None)
                self._get_date_fields(base_model=new_model,
                                      fields=fields,
                                      report_builder_fields=new_report_builder_fields,
                                      prefix=f"{include['field']}__",
                                      title_prefix=f"{include['title']} -> ",
                                      previous_base_model=base_model)
