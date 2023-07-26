import json

from crispy_forms.bootstrap import StrictButton
from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.forms import CharField, JSONField
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django_modals.forms import ModelCrispyForm
from django_modals.modals import ModelFormModal
from django_modals.widgets.select2 import Select2

from advanced_report_builder.field_types import FieldTypes
from advanced_report_builder.globals import DATE_FIELDS, NUMBER_FIELDS, LINK_COLUMNS, COLOUR_COLUMNS
from advanced_report_builder.models import ReportQuery, ReportType
from advanced_report_builder.utils import get_field_details, get_report_builder_class


class QueryBuilderModelForm(ModelCrispyForm):
    def submit_button(self, css_class='btn-success modal-submit', button_text='Submit', **kwargs):
        return StrictButton(button_text, onclick=f'save_modal_{ self.form_id }()', css_class=css_class, **kwargs)


class QueryBuilderModalBaseMixin:

    @staticmethod
    def get_report_builder_class(report_type_id):
        if not report_type_id:
            return None, None

        report_type = get_object_or_404(ReportType, pk=report_type_id)
        base_model = report_type.content_type.model_class()
        report_builder_class = get_report_builder_class(model=base_model,
                                                        report_type=report_type)
        return report_builder_class, base_model

    def get_query_builder_report_type_field(self, report_type_id):

        report_builder_class, base_model = self.get_report_builder_class(report_type_id=report_type_id)
        if report_builder_class is None:
            # noinspection PyUnresolvedReferences
            return self.command_response()
        query_builder_filters = []
        self._get_query_builder_fields(base_model=base_model,
                                       query_builder_filters=query_builder_filters,
                                       report_builder_class=report_builder_class)

        return query_builder_filters

    def _get_query_builder_fields(self, base_model, query_builder_filters, report_builder_class, prefix='',
                                  title_prefix='', previous_base_model=None):
        field_types = FieldTypes()

        for report_builder_field in report_builder_class.fields:
            if (not isinstance(report_builder_field, str) or
                    report_builder_field not in report_builder_class.exclude_search_fields):
                django_field, _, columns, _ = get_field_details(base_model=base_model,
                                                                field=report_builder_field,
                                                                report_builder_class=report_builder_class)
                for column in columns:
                    field_types.get_filter(query_builder_filters=query_builder_filters,
                                           django_field=django_field,
                                           field=column.column_name,
                                           title=title_prefix + column.title,
                                           column=column,
                                           prefix=prefix)
        for include_field, include in report_builder_class.includes.items():
            app_label, model, report_builder_fields_str = include['model'].split('.')
            new_model = apps.get_model(app_label, model)
            new_report_builder_class = get_report_builder_class(model=new_model,
                                                                class_name=report_builder_fields_str)

            if new_model != previous_base_model:
                _foreign_key = getattr(base_model, include_field, None)

                if hasattr(_foreign_key, 'field'):
                    add_null_field = _foreign_key.field.null
                else:
                    add_null_field = True

                if add_null_field:
                    field_types.get_foreign_key_null_field(query_builder_filters=query_builder_filters,
                                                           field=prefix + include_field,
                                                           title=title_prefix + include['title'])
                if isinstance(new_model(), AbstractUser):
                    field_types.get_abstract_user_field(query_builder_filters=query_builder_filters,
                                                        field=prefix + include_field,
                                                        title=title_prefix + include['title'])

                self._get_query_builder_fields(base_model=new_model,
                                               query_builder_filters=query_builder_filters,
                                               report_builder_class=new_report_builder_class,
                                               prefix=f"{prefix}{include_field}__",
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

    def add_query_data(self, form, include_extra_query=False):
        form.fields['query_data'] = JSONField(required=False, label='Filter')

        if include_extra_query:
            form.fields['extra_query_data'] = JSONField(required=False, label='Numerator filter')

        if self.object.id:
            query_id = self.slug.get('query_id')
            if query_id:
                self.report_query = get_object_or_404(ReportQuery, id=query_id)
            else:
                self.report_query = self.object.reportquery_set.first()

            if self.report_query:
                self.show_query_name = self.object.reportquery_set.count() > 1
                if self.show_query_name:
                    form.fields['query_name'] = CharField(required=True, initial=self.report_query.name)

                form.fields['query_data'].initial = self.report_query.query
                if include_extra_query:
                    form.fields['extra_query_data'].initial = self.report_query.extra_query

    @staticmethod
    def _is_search_match(search_string, title):
        if search_string is None:
            return True
        return search_string.lower() in title.lower()

    def _get_fields(self, base_model, fields, report_builder_class, tables=None,
                    prefix='', title_prefix='', title=None, colour=None,
                    previous_base_model=None, selected_field_id=None, for_select2=False,
                    pivot_fields=None, allow_annotations_fields=True, field_types=None,
                    column_types=None, search_string=None, show_order_by_fields=False, extra_fields=None):
        if title is None:
            title = report_builder_class.title
        if colour is None:
            colour = report_builder_class.colour

        if tables is not None:
            tables.append({'name': title,
                           'colour': colour})

        report_builder_class_fields = report_builder_class.fields

        if extra_fields:
            report_builder_class_fields += extra_fields

        for report_builder_field in report_builder_class_fields:

            if (not isinstance(report_builder_field, str) or
                    report_builder_field not in report_builder_class.exclude_display_fields or
                    (show_order_by_fields and report_builder_field in report_builder_class.order_by_fields)):
                django_field, col_type_override, columns, _ = get_field_details(
                    base_model=base_model,
                    field=report_builder_field,
                    report_builder_class=report_builder_class)
                for column in columns:
                    if ((field_types is None and column_types is None) or
                            (field_types is not None and isinstance(django_field, field_types)) or
                            (column_types is not None and isinstance(col_type_override, column_types)) or
                            (allow_annotations_fields and column.annotations)):
                        full_id = prefix + column.column_name
                        if selected_field_id is None or selected_field_id == full_id:

                            if column.title == '':
                                full_title = title_prefix + col_type_override.title_from_name(column.column_name)
                            else:
                                full_title = title_prefix + column.title
                            if self._is_search_match(search_string=search_string, title=full_title):
                                if for_select2:
                                    fields.append({'id': full_id,
                                                   'text': full_title})
                                else:
                                    fields.append({'field': full_id,
                                                   'label': full_title,
                                                   'colour': colour})

        if not for_select2 and pivot_fields is not None:
            for pivot_code, pivot_field in report_builder_class.pivot_fields.items():
                full_id = prefix + pivot_code
                full_title = title_prefix + pivot_field['title']
                if self._is_search_match(search_string=search_string, title=full_title):
                    pivot_fields.append({'field': full_id,
                                         'label': title_prefix + pivot_field['title'],
                                         'colour': colour})

        for include_field, include in report_builder_class.includes.items():
            app_label, model, report_builder_fields_str = include['model'].split('.')

            new_model = apps.get_model(app_label, model)
            if new_model != previous_base_model:
                new_report_builder_class = get_report_builder_class(model=new_model,
                                                                    class_name=report_builder_fields_str)
                self._get_fields(base_model=new_model,
                                 fields=fields,
                                 report_builder_class=new_report_builder_class,
                                 tables=tables,
                                 prefix=f"{prefix}{include_field}__",
                                 title_prefix=f"{title_prefix}{include['title']} -> ",
                                 title=include.get('title'),
                                 colour=include.get('colour'),
                                 previous_base_model=base_model,
                                 selected_field_id=selected_field_id,
                                 for_select2=for_select2,
                                 pivot_fields=pivot_fields,
                                 allow_annotations_fields=allow_annotations_fields,
                                 field_types=field_types,
                                 column_types=column_types,
                                 search_string=search_string,
                                 show_order_by_fields=show_order_by_fields)

    def ajax_get_fields(self, **kwargs):
        report_type_id = kwargs['report_type']
        report_builder_class, base_model = self.get_report_builder_class(report_type_id=report_type_id)
        fields = []
        tables = []
        self._get_fields(base_model=base_model,
                         fields=fields,
                         tables=tables,
                         report_builder_class=report_builder_class,
                         field_types=NUMBER_FIELDS,
                         extra_fields=report_builder_class.extra_chart_field)
        return self.command_response('report_fields', data=json.dumps({'fields': fields, 'tables': tables}))

    def _get_date_fields(self, base_model, fields, report_builder_class, selected_field_id=None, search_string=None):
        return self._get_fields(base_model=base_model,
                                fields=fields,
                                report_builder_class=report_builder_class,
                                selected_field_id=selected_field_id,
                                field_types=DATE_FIELDS,
                                for_select2=True,
                                allow_annotations_fields=False,
                                search_string=search_string)

    def _get_number_fields(self, base_model, fields, report_builder_class, selected_field_id=None, search_string=None):
        return self._get_fields(base_model=base_model,
                                fields=fields,
                                report_builder_class=report_builder_class,
                                selected_field_id=selected_field_id,
                                field_types=NUMBER_FIELDS,
                                for_select2=True,
                                search_string=search_string
                                )

    def _get_column_link_fields(self, base_model, fields, report_builder_class,
                                selected_field_id=None, search_string=None):
        return self._get_fields(base_model=base_model,
                                fields=fields,
                                report_builder_class=report_builder_class,
                                selected_field_id=selected_field_id,
                                column_types=LINK_COLUMNS,
                                for_select2=True,
                                search_string=search_string,
                                allow_annotations_fields=False
                                )

    def _get_colour_fields(self, base_model, fields, report_builder_class,
                           selected_field_id=None, search_string=None):
        return self._get_fields(base_model=base_model,
                                fields=fields,
                                report_builder_class=report_builder_class,
                                selected_field_id=selected_field_id,
                                column_types=COLOUR_COLUMNS,
                                for_select2=True,
                                search_string=search_string,
                                allow_annotations_fields=False
                                )

    def get_fields_for_select2(self, field_type, report_type, search_string):
        fields = []
        if report_type != '':
            report_builder_fields, base_model = self.get_report_builder_class(report_type_id=report_type)
            fields = []
            if field_type == 'date':
                self._get_date_fields(base_model=base_model,
                                      fields=fields,
                                      report_builder_class=report_builder_fields,
                                      search_string=search_string)
            elif field_type == 'number':
                self._get_number_fields(base_model=base_model,
                                        fields=fields,
                                        report_builder_class=report_builder_fields,
                                        search_string=search_string)
            elif field_type == 'link':
                self._get_column_link_fields(base_model=base_model,
                                             fields=fields,
                                             report_builder_class=report_builder_fields,
                                             search_string=search_string)
            elif field_type == 'colour':
                self._get_colour_fields(base_model=base_model,
                                        fields=fields,
                                        report_builder_class=report_builder_fields,
                                        search_string=search_string)
            elif field_type == 'all':
                self._get_fields(base_model=base_model,
                                 fields=fields,
                                 report_builder_class=report_builder_fields,
                                 for_select2=True,
                                 search_string=search_string)
            elif field_type == 'order':
                self._get_fields(base_model=base_model,
                                 fields=fields,
                                 report_builder_class=report_builder_fields,
                                 for_select2=True,
                                 search_string=search_string,
                                 show_order_by_fields=True)

        return JsonResponse({'results': fields})

    def setup_field(self, field_type, form, field_name, selected_field_id, report_type):
        _fields = []
        if selected_field_id:
            form.fields[field_name].initial = selected_field_id
            base_model = report_type.content_type.model_class()
            report_builder_class = get_report_builder_class(model=base_model,
                                                            report_type=report_type)
            if field_type == 'date':
                self._get_date_fields(base_model=base_model,
                                      fields=_fields,
                                      report_builder_class=report_builder_class,
                                      selected_field_id=selected_field_id)
            elif field_type == 'link':
                self._get_column_link_fields(base_model=base_model,
                                             fields=_fields,
                                             report_builder_class=report_builder_class,
                                             selected_field_id=selected_field_id)
            elif field_type == 'number':
                self._get_number_fields(base_model=base_model,
                                        fields=_fields,
                                        report_builder_class=report_builder_class,
                                        selected_field_id=selected_field_id)
            elif field_type == 'colour':
                self._get_colour_fields(base_model=base_model,
                                        fields=_fields,
                                        report_builder_class=report_builder_class,
                                        selected_field_id=selected_field_id)
            elif field_type == 'all':
                self._get_fields(base_model=base_model,
                                 fields=_fields,
                                 report_builder_class=report_builder_class,
                                 selected_field_id=selected_field_id,
                                 for_select2=True)
            elif field_type == 'order':
                self._get_fields(base_model=base_model,
                                 fields=_fields,
                                 report_builder_class=report_builder_class,
                                 selected_field_id=selected_field_id,
                                 for_select2=True,
                                 show_order_by_fields=True)

        form.fields[field_name].widget = Select2(attrs={'ajax': True})
        form.fields[field_name].widget.select_data = _fields

    def form_valid(self, form):
        org_id = self.object.id if hasattr(self, 'object') else None
        chart_report = form.save()

        extra_query_data = form.cleaned_data.get('extra_query_data')
        if not self.report_query and (form.cleaned_data['query_data'] or extra_query_data):
            ReportQuery(query=form.cleaned_data['query_data'],
                        extra_query=extra_query_data,
                        report=chart_report).save()
        elif form.cleaned_data['query_data'] or extra_query_data:
            self.report_query.extra_query = extra_query_data
            self.report_query.query = form.cleaned_data['query_data']
            if self.show_query_name:
                self.report_query.name = form.cleaned_data['query_name']
            self.report_query.save()
        elif self.report_query:
            self.report_query.delete()
        url_name = getattr(settings, 'REPORT_BUILDER_DETAIL_URL_NAME', '')
        if org_id is None and url_name:
            url = reverse(url_name, kwargs={'slug': chart_report.slug})
            return self.command_response('redirect', url=url)
        else:
            return self.command_response('reload')
