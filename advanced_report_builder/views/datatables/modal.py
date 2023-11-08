import base64
import json

from crispy_forms.bootstrap import StrictButton
from crispy_forms.layout import Div, HTML
from django.conf import settings
from django.forms import CharField, ChoiceField, BooleanField, IntegerField
from django.urls import reverse
from django_datatables.columns import MenuColumn
from django_datatables.widgets import DataTableReorderWidget
from django_menus.menu import HtmlMenu, MenuItem
from django_modals.fields import FieldEx
from django_modals.form_helpers import HorizontalNoEnterHelper
from django_modals.forms import ModelCrispyForm
from django_modals.modals import FormModal
from django_modals.processes import PROCESS_EDIT_DELETE, PERMISSION_OFF
from django_modals.widgets.select2 import Select2Multiple
from django_modals.widgets.widgets import Toggle

from advanced_report_builder.globals import DATE_FIELDS, NUMBER_FIELDS, ANNOTATION_VALUE_CHOICES, ANNOTATIONS_CHOICES, \
    DATE_FORMAT_TYPES, CURRENCY_COLUMNS, LINK_COLUMNS
from advanced_report_builder.models import TableReport, ReportQuery, ReportType
from advanced_report_builder.toggle import RBToggle
from advanced_report_builder.utils import split_attr, encode_attribute, decode_attribute, get_report_builder_class
from advanced_report_builder.views.charts_base import ChartBaseFieldForm
from advanced_report_builder.views.modals_base import QueryBuilderModalBaseMixin, QueryBuilderModalBase
from advanced_report_builder.views.query_modal.mixin import MultiQueryModalMixin


class TableModal(MultiQueryModalMixin, QueryBuilderModalBase):
    template_name = 'advanced_report_builder/datatables/modal.html'
    size = 'xl'
    model = TableReport
    process = PROCESS_EDIT_DELETE
    permission_delete = PERMISSION_OFF
    ajax_commands = ['datatable', 'button']
    show_order_by = False

    widgets = {'report_tags': Select2Multiple}

    form_fields = ['name',
                   'notes',
                   ('has_clickable_rows', {'widget': Toggle(attrs={'data-onstyle': 'success',
                                                                   'data-on': 'YES',
                                                                   'data-off': 'NO'})}),
                   'link_field',
                   'order_by_field',
                   ('order_by_ascending', {'widget': Toggle(attrs={'data-onstyle': 'success',
                                                                   'data-on': 'YES',
                                                                   'data-off': 'NO'})}),

                   'page_length',
                   'report_type',
                   'report_tags',
                   'table_fields',
                   'pivot_fields',
                   ]

    def form_setup(self, form, *_args, **_kwargs):
        url = reverse('advanced_report_builder:table_field_modal',
                      kwargs={'slug': 'selector-99999-data-FIELD_INFO-report_type_id-REPORT_TYPE_ID'})

        pivot_url = reverse('advanced_report_builder:table_pivot_modal',
                            kwargs={'slug': 'selector-99999-data-FIELD_INFO-report_type_id-REPORT_TYPE_ID'})

        form.add_trigger('has_clickable_rows', 'onchange', [
            {'selector': '#div_id_link_field', 'values': {'checked': 'show'}, 'default': 'hide'},
        ])

        form.fields['notes'].widget.attrs['rows'] = 3

        if 'data' in _kwargs:
            link_field = _kwargs['data'].get('link_field')
            order_by_field = _kwargs['data'].get('order_by_field')
            report_type_id = _kwargs['data'].get('report_type')
            report_type = ReportType.objects.filter(id=report_type_id).first()  # can be None
        else:
            link_field = form.instance.link_field
            order_by_field = form.instance.order_by_field
            report_type = form.instance.report_type

        self.setup_field(field_type='link',
                         form=form,
                         field_name='link_field',
                         selected_field_id=link_field,
                         report_type=report_type)

        self.setup_field(field_type='order',
                         form=form,
                         field_name='order_by_field',
                         selected_field_id=order_by_field,
                         report_type=report_type)

        fields = ['name',
                  'notes',
                  'report_type',
                  'report_tags',
                  FieldEx('has_clickable_rows', template='django_modals/fields/label_checkbox.html'),
                  'link_field',
                  'order_by_field',
                  FieldEx('order_by_ascending', template='django_modals/fields/label_checkbox.html'),
                  FieldEx('page_length', template='django_modals/fields/label_checkbox.html'),
                  FieldEx('table_fields',
                          template='advanced_report_builder/select_column.html',
                          extra_context={'select_column_url': url,
                                         'command_prefix': ''}),
                  FieldEx('pivot_fields',
                          template='advanced_report_builder/datatables/select_pivot.html',
                          extra_context={'select_column_url': pivot_url}),
                  ]

        if self.object.id:
            self.add_extra_queries(form=form, fields=fields, show_order_by=False)

        return fields

    def form_valid(self, form):
        org_id = self.object.pk if hasattr(self, 'object') else None
        save_function = getattr(form, 'save', None)
        if save_function:
            save_function()
        self.post_save(created=org_id is None, form=form)
        if not self.response_commands:
            self.add_command('reload')
        return self.command_response()

    def post_save(self, created, form):
        if created:
            self.modal_redirect(self.request.resolver_match.view_name, slug=f'pk-{self.object.id}-new-True')
        else:
            url_name = getattr(settings, 'REPORT_BUILDER_DETAIL_URL_NAME', '')
            if url_name and self.slug.get('new'):
                url = reverse(url_name, kwargs={'slug': self.object.slug})
                self.command_response('redirect', url=url)

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
                         pivot_fields=pivot_fields)

        self.add_command('report_fields', data=json.dumps({'fields': fields, 'tables': tables}))
        self.add_command('report_pivots', data=json.dumps({'pivot_fields': pivot_fields}))

        return self.command_response()

    def select2_link_field(self, **kwargs):
        return self.get_fields_for_select2(field_type='link',
                                           report_type=kwargs['report_type'],
                                           search_string=kwargs.get('search'))

    def select2_order_by_field(self, **kwargs):
        return self.get_fields_for_select2(field_type='order',
                                           report_type=kwargs['report_type'],
                                           search_string=kwargs.get('search'))



class TableFieldForm(ChartBaseFieldForm):
    cancel_class = 'btn-secondary modal-cancel'

    def cancel_button(self, css_class=cancel_class, **kwargs):
        commands = [{'function': 'close'}]
        return self.button('Cancel', commands, css_class, **kwargs)

    def submit_button(self, css_class='btn-success modal-submit', button_text='Submit', **kwargs):
        if self.django_field is not None and isinstance(self.django_field, NUMBER_FIELDS):
            return StrictButton(button_text, onclick=f'save_modal_{self.form_id}()', css_class=css_class, **kwargs)
        else:
            return super().submit_button(css_class, button_text, **kwargs)

    def setup_modal(self, *args, **kwargs):
        data = json.loads(base64.b64decode(self.slug['data']))
        report_type, base_model = self.get_report_type_details()

        self.fields['title'] = CharField(initial=data['title'])
        data_attr = split_attr(data)
        self.fields['display_heading'] = BooleanField(required=False,
                                                      widget=RBToggle(),
                                                      label='Display heading')
        if int(data_attr.get('display_heading', 1)) == 1:
            self.fields['display_heading'].initial = True

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
            self.fields['show_table_totals'] = BooleanField(required=False,
                                                            widget=RBToggle(),
                                                            label='Show totals')
            if 'show_totals' in data_attr and data_attr['show_totals'] == '1':
                self.fields['show_table_totals'].initial = True
            self.fields['decimal_places'] = IntegerField()
            self.fields['decimal_places'].initial = int(data_attr.get('decimal_places', 0))
            self.fields['has_filter'] = BooleanField(required=False, widget=RBToggle())

            self.fields['filter'] = CharField(required=False)

            if data_attr.get('has_filter') == '1':
                self.fields['has_filter'].initial = True
                if 'filter' in data_attr:
                    self.fields['filter'].initial = decode_attribute(data_attr['filter'])

            self.fields['multiple_columns'] = BooleanField(required=False, widget=RBToggle())

            report_builder_class = get_report_builder_class(model=base_model,
                                                            report_type=report_type)
            fields = []
            self._get_query_builder_foreign_key_fields(base_model=base_model,
                                                       report_builder_class=report_builder_class,
                                                       fields=fields)

            self.fields['multiple_column_field'] = ChoiceField(choices=fields, required=False)

            if data_attr.get('multiple_columns') == '1':
                self.fields['multiple_columns'].initial = True
                self.fields['multiple_column_field'].initial = data_attr.get('multiple_column_field')
        elif isinstance(self.col_type_override, CURRENCY_COLUMNS):
            self.fields['show_table_totals'] = BooleanField(required=False,
                                                            widget=RBToggle(),
                                                            label='Show totals')
            if 'show_totals' in data_attr and data_attr['show_totals'] == '1':
                self.fields['show_table_totals'].initial = True
        elif isinstance(self.col_type_override, LINK_COLUMNS):
            self.fields['link_html'] = CharField(required=False)
            if 'link_html' in data_attr:
                self.fields['link_html'].initial = decode_attribute(data_attr['link_html'])
            self.fields['link_css'] = CharField(required=False)
            if 'link_css' in data_attr:
                self.fields['link_css'].initial = decode_attribute(data_attr['link_css'])
            self.fields['is_icon'] = BooleanField(required=False, widget=RBToggle())
            if 'is_icon' in data_attr and data_attr['is_icon'] == '1':
                self.fields['is_icon'].initial = True
        else:
            self.fields['annotation_label'] = BooleanField(required=False, widget=RBToggle())
            if 'annotation_label' in data_attr and data_attr['annotation_label'] == '1':
                self.fields['annotation_label'].initial = True

        super().setup_modal(*args, **kwargs)

    def get_additional_attributes(self):
        attributes = []
        self.get_report_type_details()

        if self.cleaned_data['display_heading']:
            attributes.append('display_heading-1')
        else:
            attributes.append('display_heading-0')

        if self.django_field is not None and isinstance(self.django_field, DATE_FIELDS):
            if self.cleaned_data['annotations_value']:
                attributes.append(f'annotations_value-{self.cleaned_data["annotations_value"]}')
            if self.cleaned_data['date_format']:
                attributes.append(f'date_format-{self.cleaned_data["date_format"]}')
        elif self.django_field is not None and isinstance(self.django_field, NUMBER_FIELDS):
            if int(self.cleaned_data['annotations_type']) != 0:
                attributes.append(f'annotations_type-{self.cleaned_data["annotations_type"]}')
            if self.cleaned_data['show_table_totals']:
                attributes.append('show_totals-1')
            if self.cleaned_data['decimal_places'] > 0:
                attributes.append(f'decimal_places-{self.cleaned_data["decimal_places"]}')
            if self.cleaned_data['has_filter']:
                attributes.append(f'has_filter-1')
                if self.cleaned_data['filter']:
                    b64_filter = encode_attribute(self.cleaned_data['filter'])
                    attributes.append(f'filter-{b64_filter}')
                if self.cleaned_data['multiple_columns']:
                    attributes.append('multiple_columns-1')
                    attributes.append(f'multiple_column_field-{self.cleaned_data["multiple_column_field"]}')
        elif isinstance(self.col_type_override, CURRENCY_COLUMNS):
            if self.cleaned_data['show_table_totals']:
                attributes.append('show_totals-1')
        elif isinstance(self.col_type_override, LINK_COLUMNS):
            if self.cleaned_data['link_css']:
                b64_link_css = encode_attribute(self.cleaned_data['link_css'])
                attributes.append(f'link_css-{b64_link_css}')
            if self.cleaned_data['link_html']:
                b64_link_html = encode_attribute(self.cleaned_data['link_html'])
                attributes.append(f'link_html-{b64_link_html}')
            if self.cleaned_data['is_icon'] and self.cleaned_data["is_icon"]:
                attributes.append('is_icon-1')
        else:
            if self.cleaned_data['annotation_label'] and self.cleaned_data["annotation_label"]:
                attributes.append('annotation_label-1')

        if attributes:
            return '-'.join(attributes)
        return None


class TableFieldModal(QueryBuilderModalBaseMixin, FormModal):
    form_class = TableFieldForm
    size = 'xl'
    template_name = 'advanced_report_builder/datatables/fields/modal.html'
    no_header_x = True
    helper_class = HorizontalNoEnterHelper

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
        self.add_command({'function': 'update_selection'})
        return self.command_response('close')

    def form_setup(self, form, *_args, **_kwargs):

        data = json.loads(base64.b64decode(self.slug['data']))
        report_builder_class, base_model = self.get_report_builder_class(report_type_id=self.slug['report_type_id'])
        django_field, col_type_override, _, _ = self.get_field_details(base_model=base_model,
                                                                       field=data['field'],
                                                                       report_builder_class=report_builder_class)
        if django_field is not None and isinstance(django_field, NUMBER_FIELDS):
            form.add_trigger('annotations_type', 'onchange', [
                {'selector': '#annotations_fields_div', 'values': {'': 'hide'}, 'default': 'show'}])

            form.add_trigger('has_filter', 'onchange', [
                {'selector': '#filter_fields_div', 'values': {'checked': 'show'}, 'default': 'hide'}])

            form.add_trigger('multiple_columns', 'onchange', [
                {'selector': '#multiple_columns_fields_div', 'values': {'checked': 'show'}, 'default': 'hide'},
            ])

            return ['title',
                    'display_heading',
                    'annotations_type',
                    'show_table_totals',
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
        elif isinstance(col_type_override, CURRENCY_COLUMNS):
            return ['title',
                    'show_table_totals']
        elif isinstance(col_type_override, LINK_COLUMNS):
            return ['title',
                    'link_css',
                    'link_html',
                    'is_icon']

    def ajax_get_query_builder_fields(self, **kwargs):
        field_auto_id = kwargs['field_auto_id']

        report_type_id = self.slug['report_type_id']
        query_builder_filters = self.get_query_builder_report_type_field(report_type_id=report_type_id)

        return self.command_response(f'query_builder_{field_auto_id}', data=json.dumps(query_builder_filters))


class TablePivotForm(ChartBaseFieldForm):
    cancel_class = 'btn-secondary modal-cancel'

    def setup_modal(self, *args, **kwargs):
        data = json.loads(base64.b64decode(self.slug['data']))
        self.fields['title'] = CharField(initial=data['title'])
        super().setup_modal(*args, **kwargs)

    def cancel_button(self, css_class=cancel_class, **kwargs):
        commands = [{'function': 'close'}]
        return self.button('Cancel', commands, css_class, **kwargs)


class TablePivotModal(QueryBuilderModalBaseMixin, FormModal):
    form_class = TablePivotForm
    size = 'xl'
    no_header_x = True

    @property
    def modal_title(self):
        data = json.loads(base64.b64decode(self.slug['data']))
        return f'Edit {data["title"]}'

    def form_valid(self, form):
        selector = self.slug['selector']

        self.add_command({'function': 'html', 'selector': f'#{selector} span', 'html': form.cleaned_data['title']})

        self.add_command({'function': 'update_pivot_selection'})
        return self.command_response('close')


class QueryForm(ModelCrispyForm):
    cancel_class = 'btn-secondary modal-cancel'

    class Meta:
        model = ReportQuery
        fields = ['name',
                  'query']

    def submit_button(self, css_class='btn-success modal-submit', button_text='Submit', **kwargs):
        return StrictButton(button_text, onclick=f'save_modal_{self.form_id}()', css_class=css_class, **kwargs)
