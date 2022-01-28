import base64
import copy
import json

from ajax_helpers.mixins import AjaxHelpers
from crispy_forms.bootstrap import StrictButton
from crispy_forms.layout import Div
from django.db.models import Q
from django.forms import CharField, ChoiceField, BooleanField, IntegerField
from django.urls import reverse
from django_datatables.datatables import DatatableView, DatatableError
from django_datatables.plugins.column_totals import ColumnTotals
from django_menus.menu import MenuMixin, MenuItem
from django_modals.fields import FieldEx
from django_modals.modals import FormModal
from django_modals.processes import PROCESS_EDIT_DELETE, PERMISSION_OFF
from django_modals.widgets.select2 import Select2Multiple
from django_modals.widgets.widgets import Toggle

from advanced_report_builder.columns import ReportBuilderDateColumn, ReportBuilderNumberColumn
from advanced_report_builder.exceptions import ReportError
from advanced_report_builder.filter_query import FilterQueryMixin
from advanced_report_builder.globals import DATE_FIELDS, NUMBER_FIELDS, ANNOTATION_VALUE_CHOICES, ANNOTATIONS_CHOICES, \
    DATE_FORMAT_TYPES, ANNOTATION_CHOICE_COUNT
from advanced_report_builder.globals import DATE_FORMAT_TYPES_DJANGO_FORMAT, ANNOTATION_VALUE_FUNCTIONS, \
    ANNOTATION_FUNCTIONS
from advanced_report_builder.models import TableReport, ReportQuery
from advanced_report_builder.toggle import RBToggle
from advanced_report_builder.utils import split_attr, get_django_field
from advanced_report_builder.utils import split_slug
from advanced_report_builder.views.charts_base import ChartBaseFieldForm
from advanced_report_builder.views.modals_base import QueryBuilderModalBaseMixin, QueryBuilderModalBase


class TableView(AjaxHelpers, FilterQueryMixin, MenuMixin, DatatableView):
    template_name = 'advanced_report_builder/datatables/report.html'

    date_field = ReportBuilderDateColumn
    number_field = ReportBuilderNumberColumn
    menu_display = ''

    def add_tables(self):
        return None

    def dispatch(self, request, *args, **kwargs):
        self.slug = split_slug(self.kwargs['slug'])
        self.report = kwargs.get('report')
        self.table_report = self.report.tablereport
        self.dashboard_report = kwargs.get('dashboard_report')
        self.enable_edit = kwargs.get('enable_edit')
        if self.dashboard_report:
            table_id = f'tabledashboard_{self.dashboard_report.id}'
        else:
            table_id = f'table_{self.table_report.id}'

        self.base_model = self.table_report.get_base_modal()
        self.add_table(table_id, model=self.base_model)
        try:
            return super().dispatch(request, *args, **kwargs)
        except DatatableError as de:
            raise ReportError(de.args[0])

    def get_date_field(self, index, col_type_override, table_field, fields):
        data_attr = split_attr(table_field)
        field_name = table_field['field']
        date_format = data_attr.get('date_format')

        if date_format:
            date_format = DATE_FORMAT_TYPES_DJANGO_FORMAT.get(int(date_format))
        title = table_field.get('title')

        annotations_value = int(data_attr.get('annotations_value', 0))
        if col_type_override and annotations_value == 0:

            field = copy.deepcopy(col_type_override)

            if title:
                field.title = title
            fields.append(field)
        else:
            if col_type_override:
                field_name = col_type_override.field

            date_function_kwargs = {'title': table_field.get('title'),
                                    'date_format': date_format}

            if annotations_value != 0:
                new_field_name = f'{annotations_value}_{field_name}_{index}'
                function = ANNOTATION_VALUE_FUNCTIONS[annotations_value]
                date_function_kwargs['annotations_value'] = {new_field_name: function(field_name)}
                field_name = new_field_name

            date_function_kwargs.update({'field': field_name,
                                         'column_name': field_name})

            field = self.date_field(**date_function_kwargs)
            fields.append(field)

        return field_name

    def get_number_field(self, index, table_field, data_attr, fields, totals, col_type_override,
                         extra_filter=None, title_suffix=''):
        field_name = table_field['field']
        css_class = None

        annotations_type = int(data_attr.get('annotations_type', 0))
        annotation_filter = None
        if annotations_type != 0:
            b64_filter = data_attr.get('filter')
            if b64_filter:
                _filter = base64.urlsafe_b64decode(b64_filter).decode('utf-8', 'ignore')
                annotation_filter = self.process_filters(search_filter_data=_filter, extra_filter=extra_filter)
        title = title_suffix + ' ' + table_field.get('title')
        if col_type_override:
            field = copy.deepcopy(col_type_override)
            model_parts = field_name.split('__')[:-1]
            if model_parts:
                if isinstance(field.field, str):
                    field.field = '__'.join(model_parts + [field.field])

            if annotations_type == ANNOTATION_CHOICE_COUNT:
                new_field_name = f'{annotations_type}_{field_name}_{index}'
                number_function_kwargs = {}
                if title:
                    number_function_kwargs['title'] = title
                function_type = ANNOTATION_FUNCTIONS[annotations_type]
                if annotation_filter:
                    function = function_type(field.field, filter=annotation_filter)
                else:
                    function = function_type(field.field)

                number_function_kwargs['annotations'] = {new_field_name: function}

                number_function_kwargs.update({'field': new_field_name,
                                               'column_name': field_name})
                field = self.number_field(**number_function_kwargs)
            else:
                css_class = field.column_defs.get('className')
                if title:
                    field.title = title
                if annotations_type:
                    if field.annotations:
                        pass
                        # make this work if the field has already got annotations
                    else:
                        new_field_name = f'{annotations_type}_{field_name}_{index}'

                        function_type = ANNOTATION_FUNCTIONS[annotations_type]
                        if annotation_filter:
                            function = function_type(field.field, filter=annotation_filter)
                        else:
                            function = function_type(field.field)

                        field.annotations = {new_field_name: function}
                        field.field = new_field_name

            fields.append(field)
        else:
            number_function_kwargs = {'title': title}
            decimal_places = data_attr.get('decimal_places')

            if decimal_places:
                number_function_kwargs['decimal_places'] = int(decimal_places)

            if annotations_type != 0:
                new_field_name = f'{annotations_type}_{field_name}_{index}'
                function_type = ANNOTATION_FUNCTIONS[annotations_type]
                if annotation_filter:
                    function = function_type(field_name, filter=annotation_filter)
                else:
                    function = function_type(field_name)

                number_function_kwargs['annotations'] = {new_field_name: function}
                field_name = new_field_name

            number_function_kwargs.update({'field': field_name,
                                           'column_name': field_name})

            field = self.number_field(**number_function_kwargs)
            fields.append(field)

        decimal_places = data_attr.get('decimal_places', 0)
        show_total = data_attr.get('show_totals')
        if show_total == '1':
            totals[field_name] = {'sum': 'to_fixed', 'decimal_places': decimal_places, 'css_class': css_class}

        return field_name

    @staticmethod
    def _set_multiple_title(database_values, value_prefix, fields, text):
        results = {}
        for field in fields:
            value = database_values[value_prefix + '__' + field]
            results[field] = value
        return text.format(**results)

    def process_query_results(self, table):
        first_field_name = None
        base_model = self.table_report.get_base_modal()
        field_name = None
        fields = []
        totals = {}

        report_builder_class = getattr(self.base_model,
                                       self.table_report.report_type.report_builder_class_name, None)

        if len(report_builder_class.default_columns) > 0:
            fields += report_builder_class.default_columns

        if not self.table_report.table_fields:
            return fields, totals, first_field_name
        table_fields = self.table_report.get_table_fields()

        pivot_fields = self.table_report.get_pivot_fields()

        fields_used = set()
        for index, table_field in enumerate(table_fields):
            field = table_field['field']
            fields_used.add(field)

            django_field, col_type_override, _ = get_django_field(base_model=base_model, field=field)

            if isinstance(django_field, DATE_FIELDS):
                field_name = self.get_date_field(index=index,
                                                 col_type_override=col_type_override,
                                                 table_field=table_field,
                                                 fields=fields)

            elif isinstance(django_field, NUMBER_FIELDS) and (django_field is None or django_field.choices is None):
                data_attr = split_attr(table_field)

                if data_attr.get('annotations_type') and data_attr.get('multiple_columns') == '1':
                    query = self.extra_filters(query=table.model.objects)
                    multiple_column_field = data_attr.get('multiple_column_field')

                    field_report_builder_class = self._get_report_builder_class(
                        base_model=base_model,
                        field_str=multiple_column_field,
                        report_builder_class=report_builder_class)
                    _fields = field_report_builder_class.default_multiple_column_fields
                    default_multiple_column_fields = [multiple_column_field + '__' + x for x in _fields]
                    results = query.distinct(multiple_column_field).values(multiple_column_field,
                                                                           *default_multiple_column_fields)

                    for multiple_index, result in enumerate(results):
                        suffix = self._set_multiple_title(database_values=result,
                                                          value_prefix=multiple_column_field,
                                                          fields=_fields,
                                                          text=field_report_builder_class.default_multiple_column_text)
                        extra_filter = Q((multiple_column_field, result[multiple_column_field]))

                        field_name = self.get_number_field(index=f'{index}_{multiple_index}',
                                                           data_attr=data_attr,
                                                           table_field=table_field,
                                                           fields=fields,
                                                           totals=totals,
                                                           col_type_override=col_type_override,
                                                           extra_filter=extra_filter,
                                                           title_suffix=suffix)
                else:
                    field_name = self.get_number_field(index=index,
                                                       data_attr=data_attr,
                                                       table_field=table_field,
                                                       fields=fields,
                                                       totals=totals,
                                                       col_type_override=col_type_override)
            else:
                field_attr = {}
                if 'title' in table_field:
                    field_attr['title'] = table_field['title']
                field_name = field
                if field_attr:
                    field = (field, field_attr)
                fields.append(field)
            if not first_field_name:
                first_field_name = field_name
        table.add_columns(*fields)
        table.show_pivot_table = False
        if pivot_fields is not None:
            for pivot_field in pivot_fields:
                pivot_field_data = self._get_pivot_details(base_model=base_model,
                                                           pivot_str=pivot_field['field'],
                                                           report_builder_class=report_builder_class)
                if pivot_field['field'] != fields_used:
                    table.add_columns('.' + pivot_field['field'])
                    fields_used.add(pivot_field['field'])
                table.add_js_filters(pivot_field_data['type'],
                                     pivot_field['field'],
                                     filter_title=pivot_field['title'],
                                     **pivot_field_data['kwargs'])
                table.show_pivot_table = True

        if totals:
            totals[first_field_name] = {'text': 'Totals'}
            table.add_plugin(ColumnTotals, totals)

    def setup_table(self, table):
        table.extra_filters = self.extra_filters

        self.process_query_results(table=table)

        table.table_options['pageLength'] = self.table_report.page_length
        table.table_options['bStateSave'] = False

    def extra_filters(self, query):
        report_query = self.get_report_query(report=self.table_report)
        if not report_query:
            return query

        return self.process_query_filters(query=query,
                                          search_filter_data=report_query.query)

    def add_to_context(self, **kwargs):
        return {'title': self.get_title(),
                'table_report': self.table_report}

    def setup_menu(self):
        super().setup_menu()
        if self.dashboard_report and self.enable_edit:
            report_menu = self.pod_dashboard_edit_menu()
        elif self.dashboard_report and not self.enable_edit:
            report_menu = self.pod_dashboard_view_menu()
        else:
            report_menu = self.pod_report_menu()

        self.add_menu('button_menu', 'button_group').add_items(
            *report_menu,
            *self.queries_menu(),
        )

    def pod_dashboard_edit_menu(self):
        return [MenuItem(f'advanced_report_builder:dashboard_report_modal,pk-{self.dashboard_report.id}',
                         menu_display='Edit',
                         font_awesome='fas fa-pencil-alt', css_classes=['btn-primary'])]

    # noinspection PyMethodMayBeStatic
    def pod_dashboard_view_menu(self):
        return []

    def pod_report_menu(self):

        query_id = self.slug.get(f'query{self.table_report.id}')
        slug_str = ''
        if query_id:
            slug_str = f'-query_id-{query_id}'

        return [MenuItem(f'advanced_report_builder:table_modal,pk-{self.table_report.id}{slug_str}',
                         menu_display='Edit',
                         font_awesome='fas fa-pencil-alt', css_classes=['btn-primary'])]

    @staticmethod
    def edit_report_menu(chart_report_id, slug_str):
        return [MenuItem(f'advanced_report_builder:table_modal,pk-{chart_report_id}{slug_str}',
                         menu_display='Edit',
                         font_awesome='fas fa-pencil-alt', css_classes=['btn-primary'])]

    def queries_menu(self):
        return []


class TableModal(QueryBuilderModalBase):
    template_name = 'advanced_report_builder/datatables/modal.html'
    size = 'xl'
    model = TableReport
    process = PROCESS_EDIT_DELETE
    permission_delete = PERMISSION_OFF

    widgets = {'report_tags': Select2Multiple}

    form_fields = ['name',
                   ('has_clickable_rows', {'widget': Toggle(attrs={'data-onstyle': 'success',
                                                                   'data-on': 'YES',
                                                                   'data-off': 'NO'})}),
                   'page_length',
                   'report_type',
                   'report_tags',
                   'table_fields',
                   'pivot_fields',
                   ]

    def __init__(self, *args, **kwargs):
        self.report_query = None
        self.show_query_name = False
        super().__init__(*args, **kwargs)

    def form_setup(self, form, *_args, **_kwargs):
        self.add_query_data(form)
        url = reverse('advanced_report_builder:table_field_modal',
                      kwargs={'slug': 'selector-99999-data-FIELD_INFO-report_type_id-REPORT_TYPE_ID'})

        pivot_url = reverse('advanced_report_builder:table_pivot_modal',
                            kwargs={'slug': 'selector-99999-data-FIELD_INFO-report_type_id-REPORT_TYPE_ID'})

        fields = ['name',
                  'report_type',
                  'report_tags',
                  FieldEx('has_clickable_rows', template='django_modals/fields/label_checkbox.html'),
                  FieldEx('page_length', template='django_modals/fields/label_checkbox.html'),
                  FieldEx('table_fields',
                          template='advanced_report_builder/select_column.html',
                          extra_context={'select_column_url': url}),
                  FieldEx('pivot_fields',
                          template='advanced_report_builder/datatables/select_pivot.html',
                          extra_context={'select_column_url': pivot_url}),
                  ]

        if self.show_query_name:
            fields.append(FieldEx('query_name'))

        fields.append(FieldEx('query_data', template='advanced_report_builder/query_builder.html'))
        return fields

    def form_valid(self, form):
        table_report = form.save()

        if not self.report_query and form.cleaned_data['query_data']:
            ReportQuery(query=form.cleaned_data['query_data'],
                        report=table_report).save()
        elif form.cleaned_data['query_data']:
            self.report_query.query = form.cleaned_data['query_data']
            if self.show_query_name:
                self.report_query.name = form.cleaned_data['query_name']
            self.report_query.save()
        elif self.report_query:
            self.report_query.delete()

        return self.command_response('reload')

    def ajax_get_fields(self, **kwargs):
        report_type_id = kwargs['report_type']
        report_builder_class, base_model = self.get_report_builder_class(report_type_id=report_type_id)
        fields = []
        tables = []
        pivot_fields = []
        self._get_fields(base_model=base_model,
                         fields=fields,
                         tables=tables,
                         report_builder_class=report_builder_class,
                         all_fields=True,
                         pivot_fields=pivot_fields)

        self.add_command('report_fields', data=json.dumps({'fields': fields, 'tables': tables}))
        self.add_command('report_pivots', data=json.dumps({'pivot_fields': pivot_fields}))

        return self.command_response()


class TableFieldForm(ChartBaseFieldForm):

    def submit_button(self, css_class='btn-success modal-submit', button_text='Submit', **kwargs):
        if((self.django_field is not None and isinstance(self.django_field, NUMBER_FIELDS)) or
           (self.col_type_override is not None and self.col_type_override.annotations)):
            return StrictButton(button_text, onclick=f'save_modal_{self.form_id}()', css_class=css_class, **kwargs)
        else:
            return super().submit_button(css_class, button_text, **kwargs)

    def setup_modal(self, *args, **kwargs):
        data = json.loads(base64.b64decode(self.slug['data']))
        report_type, base_model = self.get_report_type_details()

        self.fields['title'] = CharField(initial=data['title'])

        data_attr = split_attr(data)
        if self.django_field is not None and isinstance(self.django_field, DATE_FIELDS):
            self.fields['annotations_value'] = ChoiceField(choices=[(0, '-----')] + ANNOTATION_VALUE_CHOICES,
                                                           required=False)
            if 'annotations_value' in data_attr:
                self.fields['annotations_value'].initial = data_attr['annotations_value']
            self.fields['date_format'] = ChoiceField(choices=[(0, '-----')] + DATE_FORMAT_TYPES, required=False)
            if 'date_format' in data_attr:
                self.fields['date_format'].initial = data_attr['date_format']
        elif self.django_field is not None and isinstance(self.django_field, NUMBER_FIELDS):
            self.fields['annotations_type'] = ChoiceField(choices=[(0, '-----')] + ANNOTATIONS_CHOICES,
                                                          required=False)
            if 'annotations_type' in data_attr:
                self.fields['annotations_type'].initial = data_attr['annotations_type']
            self.fields['show_totals'] = BooleanField(required=False, widget=RBToggle())
            if 'show_totals' in data_attr and data_attr['show_totals'] == '1':
                self.fields['show_totals'].initial = True
            self.fields['decimal_places'] = IntegerField()
            self.fields['decimal_places'].initial = int(data_attr.get('decimal_places', 0))
            self.fields['has_filter'] = BooleanField(required=False, widget=RBToggle())

            self.fields['filter'] = CharField(required=False)

            if data_attr.get('has_filter') == '1':
                self.fields['has_filter'].initial = True
                if 'filter' in data_attr:
                    _filter = base64.urlsafe_b64decode(data_attr['filter'])
                    _filter = _filter.decode('utf-8', 'ignore')
                    self.fields['filter'].initial = _filter

            self.fields['multiple_columns'] = BooleanField(required=False, widget=RBToggle())

            report_builder_fields = getattr(base_model, report_type.report_builder_class_name, None)
            fields = []
            self._get_query_builder_foreign_key_fields(base_model=base_model,
                                                       report_builder_fields=report_builder_fields,
                                                       fields=fields)

            self.fields['multiple_column_field'] = ChoiceField(choices=fields, required=False)

            if data_attr.get('multiple_columns') == '1':
                self.fields['multiple_columns'].initial = True
                self.fields['multiple_column_field'].initial = data_attr.get('multiple_column_field')

        super().setup_modal(*args, **kwargs)

    def get_additional_attributes(self):
        attributes = []
        self.get_report_type_details()
        if self.django_field is not None and isinstance(self.django_field, DATE_FIELDS):
            if self.cleaned_data['annotations_value']:
                attributes.append(f'annotations_value-{self.cleaned_data["annotations_value"]}')
            if self.cleaned_data['date_format']:
                attributes.append(f'date_format-{self.cleaned_data["date_format"]}')
        elif self.django_field is not None and isinstance(self.django_field, NUMBER_FIELDS):
            if int(self.cleaned_data['annotations_type']) != 0:
                attributes.append(f'annotations_type-{self.cleaned_data["annotations_type"]}')
            if self.cleaned_data['show_totals'] and self.cleaned_data["show_totals"]:
                attributes.append('show_totals-1')
            if self.cleaned_data['decimal_places'] > 0:
                attributes.append(f'decimal_places-{self.cleaned_data["decimal_places"]}')

            if self.cleaned_data['has_filter']:
                attributes.append(f'has_filter-1')

                if self.cleaned_data['filter']:
                    _filter = self.cleaned_data['filter'].encode('utf-8', 'ignore')
                    b64_filter = base64.urlsafe_b64encode(_filter).decode('utf-8', 'ignore')
                    attributes.append(f'filter-{b64_filter}')

                if self.cleaned_data['multiple_columns']:
                    attributes.append('multiple_columns-1')
                    attributes.append(f'multiple_column_field-{self.cleaned_data["multiple_column_field"]}')

        if attributes:
            return '-'.join(attributes)
        return None


class TableFieldModal(QueryBuilderModalBaseMixin, FormModal):
    form_class = TableFieldForm
    size = 'xl'
    template_name = 'advanced_report_builder/datatables/fields/modal.html'

    @property
    def modal_title(self):
        data = json.loads(base64.b64decode(self.slug['data']))
        return f'Edit {data["title"]}'

    def form_valid(self, form):
        selector = self.slug['selector']

        _attr = form.get_additional_attributes()
        self.add_command({'function': 'set_attr',
                          'selector': f'#{selector}',
                          'attr': 'data-attr',
                          'val': _attr})

        self.add_command({'function': 'html', 'selector': f'#{selector} span', 'html': form.cleaned_data['title']})
        self.add_command({'function': 'save_query_builder_id_query_data'})
        self.add_command({'function': 'update_selection'})
        return self.command_response('close')

    def form_setup(self, form, *_args, **_kwargs):

        data = json.loads(base64.b64decode(self.slug['data']))
        report_builder_fields, base_model = self.get_report_builder_class(report_type_id=self.slug['report_type_id'])
        django_field, col_type_override, _ = get_django_field(base_model=base_model, field=data['field'])
        if django_field is not None and isinstance(django_field, NUMBER_FIELDS):
            form.add_trigger('annotations_type', 'onchange', [
                {'selector': '#annotations_fields_div', 'values': {'': 'hide'}, 'default': 'show'}])

            form.add_trigger('has_filter', 'onchange', [
                {'selector': '#filter_fields_div', 'values': {'checked': 'show'}, 'default': 'hide'}])

            form.add_trigger('multiple_columns', 'onchange', [
                {'selector': '#multiple_columns_fields_div', 'values': {'checked': 'show'}, 'default': 'hide'},
            ])

            return ['title',
                    'annotations_type',
                    'show_totals',
                    'decimal_places',
                    Div(FieldEx('has_filter',
                                template='django_modals/fields/label_checkbox.html',
                                field_class='col-6 input-group-sm'),
                        Div(
                            FieldEx('filter',
                                    template='advanced_report_builder/datatables/fields/single_query_builder.html'),
                            FieldEx('multiple_columns',
                                    template='django_modals/fields/label_checkbox.html',
                                    field_class='col-6 input-group-sm'),
                            Div(
                                FieldEx('multiple_column_field'),
                                css_id='multiple_columns_fields_div'),
                            css_id='filter_fields_div'),
                        css_id='annotations_fields_div')
                    ]

    def ajax_get_query_builder_fields(self, **kwargs):
        field_auto_id = kwargs['field_auto_id']

        report_type_id = self.slug['report_type_id']
        query_builder_filters = self.get_query_builder_report_type_field(report_type_id=report_type_id)

        return self.command_response(f'query_builder_{field_auto_id}', data=json.dumps(query_builder_filters))


class TablePivotForm(ChartBaseFieldForm):
    def setup_modal(self, *args, **kwargs):
        data = json.loads(base64.b64decode(self.slug['data']))
        self.fields['title'] = CharField(initial=data['title'])
        super().setup_modal(*args, **kwargs)


class TablePivotModal(QueryBuilderModalBaseMixin, FormModal):
    form_class = TablePivotForm
    size = 'xl'

    @property
    def modal_title(self):
        data = json.loads(base64.b64decode(self.slug['data']))
        return f'Edit {data["title"]}'

    def form_valid(self, form):
        selector = self.slug['selector']

        self.add_command({'function': 'html', 'selector': f'#{selector} span', 'html': form.cleaned_data['title']})
        self.add_command({'function': 'save_query_builder_id_query_data'})
        self.add_command({'function': 'update_pivot_selection'})
        return self.command_response('close')
