import base64
import json

from crispy_forms.bootstrap import StrictButton
from crispy_forms.layout import Div
from django.apps import apps
from django.forms import BooleanField, CharField, ChoiceField, IntegerField
from django.urls import reverse
from django_modals.fields import FieldEx
from django_modals.form_helpers import HorizontalNoEnterHelper
from django_modals.modals import FormModal
from django_modals.processes import PERMISSION_OFF, PROCESS_EDIT_DELETE
from django_modals.widgets.select2 import Select2Multiple
from django_modals.widgets.widgets import Toggle

from advanced_report_builder.column_types import (
    CURRENCY_COLUMNS,
    DATE_FIELDS,
    LINK_COLUMNS,
    NUMBER_FIELDS,
    REVERSE_FOREIGN_KEY_BOOL_COLUMNS,
    REVERSE_FOREIGN_KEY_CHOICE_COLUMNS,
    REVERSE_FOREIGN_KEY_DATE_COLUMNS,
    REVERSE_FOREIGN_KEY_STR_COLUMNS,
)
from advanced_report_builder.globals import (
    ALIGNMENT_CHOICE_RIGHT,
    ALIGNMENT_CHOICES,
    ANNOTATION_VALUE_CHOICES,
    ANNOTATIONS_CHOICES,
    DATE_FORMAT_TYPES,
    REVERSE_FOREIGN_KEY_ANNOTATION_BOOLEAN_CHOICES,
    REVERSE_FOREIGN_KEY_ANNOTATION_DATE_ARRAY,
    REVERSE_FOREIGN_KEY_ANNOTATION_DATE_CHOICES,
    REVERSE_FOREIGN_KEY_DELIMITER_CHOICES,
)
from advanced_report_builder.models import ReportType, TableReport
from advanced_report_builder.toggle import RBToggle
from advanced_report_builder.utils import (
    decode_attribute,
    encode_attribute,
    get_report_builder_class,
    split_attr,
)
from advanced_report_builder.views.charts_base import ChartBaseFieldForm
from advanced_report_builder.views.modals_base import (
    QueryBuilderModalBase,
    QueryBuilderModalBaseMixin,
)
from advanced_report_builder.views.query_modal.mixin import MultiQueryModalMixin


class TableModal(MultiQueryModalMixin, QueryBuilderModalBase):
    template_name = 'advanced_report_builder/datatables/modal.html'
    size = 'xl'
    model = TableReport
    process = PROCESS_EDIT_DELETE
    permission_delete = PERMISSION_OFF
    show_order_by = False

    widgets = {'report_tags': Select2Multiple}

    form_fields = [
        'name',
        'notes',
        (
            'has_clickable_rows',
            {
                'widget': Toggle(
                    attrs={
                        'data-onstyle': 'success',
                        'data-on': 'YES',
                        'data-off': 'NO',
                    }
                )
            },
        ),
        'link_field',
        'order_by_field',
        (
            'order_by_ascending',
            {
                'widget': Toggle(
                    attrs={
                        'data-onstyle': 'success',
                        'data-on': 'YES',
                        'data-off': 'NO',
                    }
                )
            },
        ),
        'page_length',
        'report_type',
        'report_tags',
        'table_fields',
        'pivot_fields',
    ]

    def form_setup(self, form, *_args, **_kwargs):
        url = reverse(
            'advanced_report_builder:table_field_modal',
            kwargs={'slug': 'selector-99999-data-FIELD_INFO-report_type_id-REPORT_TYPE_ID'},
        )

        pivot_url = reverse(
            'advanced_report_builder:table_pivot_modal',
            kwargs={'slug': 'selector-99999-data-FIELD_INFO-report_type_id-REPORT_TYPE_ID'},
        )

        form.add_trigger(
            'has_clickable_rows',
            'onchange',
            [
                {
                    'selector': '#div_id_link_field',
                    'values': {'checked': 'show'},
                    'default': 'hide',
                },
            ],
        )

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

        self.setup_field(
            field_type='link',
            form=form,
            field_name='link_field',
            selected_field_id=link_field,
            report_type=report_type,
        )

        self.setup_field(
            field_type='order',
            form=form,
            field_name='order_by_field',
            selected_field_id=order_by_field,
            report_type=report_type,
        )

        fields = [
            'name',
            'notes',
            'report_type',
            'report_tags',
            FieldEx(
                'has_clickable_rows',
                template='django_modals/fields/label_checkbox.html',
            ),
            'link_field',
            'order_by_field',
            FieldEx(
                'order_by_ascending',
                template='django_modals/fields/label_checkbox.html',
            ),
            FieldEx('page_length', template='django_modals/fields/label_checkbox.html'),
            FieldEx(
                'table_fields',
                template='advanced_report_builder/select_column.html',
                extra_context={'select_column_url': url, 'command_prefix': ''},
            ),
            FieldEx(
                'pivot_fields',
                template='advanced_report_builder/datatables/select_pivot.html',
                extra_context={'select_column_url': pivot_url},
            ),
        ]

        if self.object.id:
            self.add_extra_queries(form=form, fields=fields)

        return fields

    def form_valid(self, form):
        org_id = self.object.pk if hasattr(self, 'object') else None
        instance = form.save(commit=False)
        instance._current_user = self.request.user
        instance.save()
        self.post_save(created=org_id is None, form=form)
        if not self.response_commands:
            self.add_command('reload')
        return self.command_response()

    def ajax_get_fields(self, **kwargs):
        report_type_id = kwargs['report_type']
        report_builder_class, base_model = self.get_report_builder_class(report_type_id=report_type_id)
        fields = []
        tables = []
        pivot_fields = []
        self._get_fields(
            base_model=base_model,
            fields=fields,
            tables=tables,
            report_builder_class=report_builder_class,
            pivot_fields=pivot_fields,
            include_mathematical_columns=True,
        )

        self.add_command('report_fields', data=json.dumps({'fields': fields, 'tables': tables}))
        self.add_command('report_pivots', data=json.dumps({'pivot_fields': pivot_fields}))

        return self.command_response()

    def select2_link_field(self, **kwargs):
        return self.get_fields_for_select2(
            field_type='link',
            report_type=kwargs['report_type'],
            search_string=kwargs.get('search'),
        )

    def select2_order_by_field(self, **kwargs):
        return self.get_fields_for_select2(
            field_type='order',
            report_type=kwargs['report_type'],
            search_string=kwargs.get('search'),
        )


class TableFieldForm(ChartBaseFieldForm):
    cancel_class = 'btn-secondary modal-cancel'

    def cancel_button(self, css_class=cancel_class, **kwargs):
        commands = [{'function': 'close'}]
        return self.button('Cancel', commands, css_class, **kwargs)

    def submit_button(self, css_class='btn-success modal-submit', button_text='Submit', **kwargs):
        if self.django_field is not None and isinstance(self.django_field, NUMBER_FIELDS + CURRENCY_COLUMNS):
            return StrictButton(
                button_text,
                onclick=f'save_modal_{self.form_id}()',
                css_class=css_class,
                **kwargs,
            )
        else:
            return super().submit_button(css_class, button_text, **kwargs)

    def is_mathematical_field(self, data):
        return self.django_field is None and data['field'] in [
            'rb_addition',
            'rb_subtraction',
            'rb_times',
            'rb_division',
            'rb_percentage',
        ]

    def setup_modal(self, *args, **kwargs):
        data = json.loads(base64.b64decode(self.slug['data']))
        report_type, base_model = self.get_report_type_details()

        self.fields['title'] = CharField(initial=data['title'])
        data_attr = split_attr(data)
        self.fields['display_heading'] = BooleanField(required=False, widget=RBToggle(), label='Display heading')
        if int(data_attr.get('display_heading', 1)) == 1:
            self.fields['display_heading'].initial = True

        has_existing_annotations = self.col_type_override is not None and self.col_type_override.annotations is not None

        if self.django_field is not None and isinstance(self.django_field, DATE_FIELDS):
            self.setup_date_fields(data_attr)
        elif self.django_field is not None and isinstance(self.django_field, NUMBER_FIELDS):
            self.setup_number_fields(
                data_attr=data_attr,
                base_model=base_model,
                report_type=report_type,
                has_existing_annotations=has_existing_annotations,
            )
        elif isinstance(self.col_type_override, CURRENCY_COLUMNS):
            self.setup_currency_fields(
                data_attr=data_attr,
                base_model=base_model,
                report_type=report_type,
                has_existing_annotations=has_existing_annotations,
            )
        elif isinstance(self.col_type_override, LINK_COLUMNS):
            self.setup_link_fields(data_attr=data_attr)
        elif isinstance(self.col_type_override, REVERSE_FOREIGN_KEY_STR_COLUMNS):
            self.setup_reverse_foreign_str_key(data_attr=data_attr)
        elif isinstance(self.col_type_override, REVERSE_FOREIGN_KEY_BOOL_COLUMNS):
            self.setup_reverse_foreign_bool_key(data_attr=data_attr)
        elif isinstance(self.col_type_override, REVERSE_FOREIGN_KEY_CHOICE_COLUMNS):
            self.setup_reverse_foreign_choice_key(data_attr=data_attr)
        elif isinstance(self.col_type_override, REVERSE_FOREIGN_KEY_DATE_COLUMNS):
            self.setup_reverse_foreign_date_key(data_attr=data_attr)
        elif self.col_type_override.annotations is not None:
            self.setup_annotation_fields(data_attr=data_attr)
        elif self.is_mathematical_field(data=data):
            self.setup_standard_mathematical_fields(data=data, data_attr=data_attr)
        else:
            self.fields['annotation_label'] = BooleanField(required=False, widget=RBToggle())
            if 'annotation_label' in data_attr and data_attr['annotation_label'] == '1':
                self.fields['annotation_label'].initial = True
        super().setup_modal(*args, **kwargs)

    def setup_annotation_fields(self, data_attr):
        self.fields['show_table_totals'] = BooleanField(required=False, widget=RBToggle(), label='Show totals')
        if 'show_totals' in data_attr and data_attr['show_totals'] == '1':
            self.fields['show_table_totals'].initial = True

    def setup_currency_fields(self, data_attr, base_model, report_type, has_existing_annotations):
        if has_existing_annotations:
            self.fields['append_annotation_query'] = BooleanField(
                required=False, widget=RBToggle(), label='Append annotation query'
            )
            if 'append_annotation_query' in data_attr and data_attr['append_annotation_query'] == '1':
                self.fields['append_annotation_query'].initial = True
        else:
            self.fields['annotations_type'] = ChoiceField(choices=[(0, '-----')] + ANNOTATIONS_CHOICES, required=False)
            if 'annotations_type' in data_attr:
                self.fields['annotations_type'].initial = data_attr['annotations_type']
            else:
                self.fields['alignment'].initial = ALIGNMENT_CHOICE_RIGHT

        annotation_column_help_text = 'Not required however useful for mathematical columns.'
        self.fields['annotation_column_id'] = CharField(required=False, help_text=annotation_column_help_text)
        if 'annotation_column_id' in data_attr:
            self.fields['annotation_column_id'].initial = decode_attribute(data_attr['annotation_column_id'])

        self.fields['show_table_totals'] = BooleanField(required=False, widget=RBToggle(), label='Show totals')
        if 'show_totals' in data_attr and data_attr['show_totals'] == '1':
            self.fields['show_table_totals'].initial = True

        self.fields['alignment'] = ChoiceField(choices=ALIGNMENT_CHOICES, required=False)
        if 'alignment' in data_attr:
            self.fields['alignment'].initial = data_attr['alignment']
        else:
            self.fields['alignment'].initial = ALIGNMENT_CHOICE_RIGHT
        self.fields['has_filter'] = BooleanField(required=False, widget=RBToggle())

        self.fields['filter'] = CharField(required=False)

        if data_attr.get('has_filter') == '1':
            self.fields['has_filter'].initial = True
            if 'filter' in data_attr:
                self.fields['filter'].initial = decode_attribute(data_attr['filter'])

        self.fields['multiple_columns'] = BooleanField(required=False, widget=RBToggle())

        report_builder_class = get_report_builder_class(model=base_model, report_type=report_type)
        fields = []
        self._get_query_builder_foreign_key_fields(
            base_model=base_model,
            report_builder_class=report_builder_class,
            fields=fields,
        )

        self.fields['multiple_column_field'] = ChoiceField(choices=fields, required=False)

        if data_attr.get('multiple_columns') == '1':
            self.fields['multiple_columns'].initial = True
            self.fields['multiple_column_field'].initial = data_attr.get('multiple_column_field')
            if data_attr.get('append_column_title') == '1':
                self.fields['append_column_title'].initial = True

    def setup_link_fields(self, data_attr):
        self.fields['link_html'] = CharField(required=False)
        if 'link_html' in data_attr:
            self.fields['link_html'].initial = decode_attribute(data_attr['link_html'])
        self.fields['link_css'] = CharField(required=False)
        if 'link_css' in data_attr:
            self.fields['link_css'].initial = decode_attribute(data_attr['link_css'])
        self.fields['is_icon'] = BooleanField(required=False, widget=RBToggle())
        if 'is_icon' in data_attr and data_attr['is_icon'] == '1':
            self.fields['is_icon'].initial = True

    def setup_reverse_foreign_str_key(self, data_attr):
        self.fields['delimiter_type'] = ChoiceField(choices=REVERSE_FOREIGN_KEY_DELIMITER_CHOICES, required=False)
        if 'delimiter_type' in data_attr:
            self.fields['delimiter_type'].initial = data_attr['delimiter_type']
        self.fields['has_filter'] = BooleanField(required=False, widget=RBToggle())
        self.fields['filter'] = CharField(required=False)
        if data_attr.get('has_filter') == '1':
            self.fields['has_filter'].initial = True
            if 'filter' in data_attr:
                self.fields['filter'].initial = decode_attribute(data_attr['filter'])

    def setup_reverse_foreign_bool_key(self, data_attr):
        self.fields['annotations_type'] = ChoiceField(
            choices=REVERSE_FOREIGN_KEY_ANNOTATION_BOOLEAN_CHOICES,
            required=False,
            label='Type',
        )
        if 'annotations_type' in data_attr:
            self.fields['annotations_type'].initial = data_attr['annotations_type']
        self.fields['has_filter'] = BooleanField(required=False, widget=RBToggle())
        self.fields['filter'] = CharField(required=False)
        if data_attr.get('has_filter') == '1':
            self.fields['has_filter'].initial = True
            if 'filter' in data_attr:
                self.fields['filter'].initial = decode_attribute(data_attr['filter'])

    def setup_reverse_foreign_choice_key(self, data_attr):
        self.fields['delimiter_type'] = ChoiceField(choices=REVERSE_FOREIGN_KEY_DELIMITER_CHOICES, required=False)
        if 'delimiter_type' in data_attr:
            self.fields['delimiter_type'].initial = data_attr['delimiter_type']
        self.fields['has_filter'] = BooleanField(required=False, widget=RBToggle())
        self.fields['filter'] = CharField(required=False)
        if data_attr.get('has_filter') == '1':
            self.fields['has_filter'].initial = True
            if 'filter' in data_attr:
                self.fields['filter'].initial = decode_attribute(data_attr['filter'])

    def setup_reverse_foreign_date_key(self, data_attr):
        self.fields['annotations_type'] = ChoiceField(
            choices=REVERSE_FOREIGN_KEY_ANNOTATION_DATE_CHOICES,
            required=False,
            label='Type',
        )
        if 'annotations_type' in data_attr:
            self.fields['annotations_type'].initial = data_attr['annotations_type']
        self.fields['delimiter_type'] = ChoiceField(choices=REVERSE_FOREIGN_KEY_DELIMITER_CHOICES, required=False)
        if 'delimiter_type' in data_attr:
            self.fields['delimiter_type'].initial = data_attr['delimiter_type']
        self.fields['date_format'] = ChoiceField(choices=[(0, '-----')] + DATE_FORMAT_TYPES, required=False)
        if 'date_format' in data_attr:
            self.fields['date_format'].initial = data_attr['date_format']
        self.fields['has_filter'] = BooleanField(required=False, widget=RBToggle())
        self.fields['filter'] = CharField(required=False)
        if data_attr.get('has_filter') == '1':
            self.fields['has_filter'].initial = True
            if 'filter' in data_attr:
                self.fields['filter'].initial = decode_attribute(data_attr['filter'])

    def setup_date_fields(self, data_attr):
        self.fields['annotations_value'] = ChoiceField(
            choices=[(0, '-----')] + ANNOTATION_VALUE_CHOICES, required=False
        )
        if 'annotations_value' in data_attr:
            self.fields['annotations_value'].initial = data_attr['annotations_value']
        self.fields['date_format'] = ChoiceField(choices=[(0, '-----')] + DATE_FORMAT_TYPES, required=False)
        if 'date_format' in data_attr:
            self.fields['date_format'].initial = data_attr['date_format']

    def setup_number_fields(self, data_attr, base_model, report_type, has_existing_annotations):
        if has_existing_annotations:
            self.fields['append_annotation_query'] = BooleanField(
                required=False, widget=RBToggle(), label='Append annotation query'
            )
            if 'append_annotation_query' in data_attr and data_attr['append_annotation_query'] == '1':
                self.fields['append_annotation_query'].initial = True
        else:
            self.fields['annotations_type'] = ChoiceField(choices=[(0, '-----')] + ANNOTATIONS_CHOICES, required=False)
            if 'annotations_type' in data_attr:
                self.fields['annotations_type'].initial = data_attr['annotations_type']

        annotation_column_help_text = 'Not required however useful for mathematical columns.'
        self.fields['annotation_column_id'] = CharField(required=False, help_text=annotation_column_help_text)
        if 'annotation_column_id' in data_attr:
            self.fields['annotation_column_id'].initial = decode_attribute(data_attr['annotation_column_id'])

        self.fields['show_table_totals'] = BooleanField(required=False, widget=RBToggle(), label='Show totals')
        if 'show_totals' in data_attr and data_attr['show_totals'] == '1':
            self.fields['show_table_totals'].initial = True

        self.fields['alignment'] = ChoiceField(choices=ALIGNMENT_CHOICES, required=False)
        if 'alignment' in data_attr:
            self.fields['alignment'].initial = data_attr['alignment']
        else:
            self.fields['alignment'].initial = ALIGNMENT_CHOICE_RIGHT

        self.fields['decimal_places'] = IntegerField()
        self.fields['decimal_places'].initial = int(data_attr.get('decimal_places', 0))
        self.fields['has_filter'] = BooleanField(required=False, widget=RBToggle())

        self.fields['filter'] = CharField(required=False)

        if data_attr.get('has_filter') == '1':
            self.fields['has_filter'].initial = True
            if 'filter' in data_attr:
                self.fields['filter'].initial = decode_attribute(data_attr['filter'])

        self.fields['multiple_columns'] = BooleanField(required=False, widget=RBToggle())

        report_builder_class = get_report_builder_class(model=base_model, report_type=report_type)
        fields = []
        self._get_query_builder_foreign_key_fields(
            base_model=base_model,
            report_builder_class=report_builder_class,
            fields=fields,
        )

        self.fields['multiple_column_field'] = ChoiceField(choices=fields, required=False)

        if data_attr.get('multiple_columns') == '1':
            self.fields['multiple_columns'].initial = True
            self.fields['multiple_column_field'].initial = data_attr.get('multiple_column_field')
            if data_attr.get('append_column_title') == '1':
                self.fields['append_column_title'].initial = True

    def setup_standard_mathematical_fields(self, data, data_attr):
        self.fields['hidden'] = BooleanField(required=False, widget=RBToggle(), label='Hidden')
        if int(data_attr.get('hidden', 0)) == 1:
            self.fields['hidden'].initial = True

        self.fields['column_id'] = CharField(required=False)
        if 'column_id' in data_attr:
            self.fields['column_id'].initial = decode_attribute(data_attr['column_id'])
        if data['field'] in ['rb_division', 'rb_percentage']:
            self.fields['numerator_column'] = CharField(required=False)
            if 'numerator_column' in data_attr:
                self.fields['numerator_column'].initial = decode_attribute(data_attr['numerator_column'])
            self.fields['denominator_column'] = CharField(required=False)
            if 'denominator_column' in data_attr:
                self.fields['denominator_column'].initial = decode_attribute(data_attr['denominator_column'])
        elif data['field'] == 'rb_times':
            self.fields['multiplicand_column'] = CharField(required=False)
            if 'multiplicand_column' in data_attr:
                self.fields['multiplicand_column'].initial = decode_attribute(data_attr['multiplicand_column'])
            self.fields['multiplier_column'] = CharField(required=False)
            if 'multiplier_column' in data_attr:
                self.fields['multiplier_column'].initial = decode_attribute(data_attr['multiplier_column'])
        else:  # add and sub
            self.fields['first_value_column'] = CharField(required=False)
            if 'first_value_column' in data_attr:
                self.fields['first_value_column'].initial = decode_attribute(data_attr['first_value_column'])
            self.fields['second_value_column'] = CharField(required=False)
            if 'second_value_column' in data_attr:
                self.fields['second_value_column'].initial = decode_attribute(data_attr['second_value_column'])
        self.fields['decimal_places'] = IntegerField()
        self.fields['decimal_places'].initial = int(data_attr.get('decimal_places', 0))
        self.fields['show_table_totals'] = BooleanField(required=False, widget=RBToggle(), label='Show totals')
        if 'show_totals' in data_attr and data_attr['show_totals'] == '1':
            self.fields['show_table_totals'].initial = True

        self.fields['alignment'] = ChoiceField(choices=ALIGNMENT_CHOICES, required=False)
        if 'alignment' in data_attr:
            self.fields['alignment'].initial = data_attr['alignment']
        else:
            self.fields['alignment'].initial = ALIGNMENT_CHOICE_RIGHT

    def save_mathematical_fields(self, data, attributes):
        if self.cleaned_data['hidden']:
            attributes.append('hidden-1')

        alignment = self.cleaned_data.get('alignment')
        attributes.append(f'alignment-{alignment}')
        if self.cleaned_data['column_id']:
            b64_column_id = encode_attribute(self.cleaned_data['column_id'])
            attributes.append(f'column_id-{b64_column_id}')
        if data['field'] in ['rb_division', 'rb_percentage']:
            if self.cleaned_data['numerator_column']:
                b64_numerator_column = encode_attribute(self.cleaned_data['numerator_column'])
                attributes.append(f'numerator_column-{b64_numerator_column}')
            if self.cleaned_data['denominator_column']:
                b64_denominator_column = encode_attribute(self.cleaned_data['denominator_column'])
                attributes.append(f'denominator_column-{b64_denominator_column}')
        elif data['field'] == 'rb_times':
            if self.cleaned_data['multiplicand_column']:
                b64_multiplicand_column = encode_attribute(self.cleaned_data['multiplicand_column'])
                attributes.append(f'multiplicand_column-{b64_multiplicand_column}')
            if self.cleaned_data['multiplier_column']:
                b64_multiplier_column = encode_attribute(self.cleaned_data['multiplier_column'])
                attributes.append(f'multiplier_column-{b64_multiplier_column}')
        else:
            if self.cleaned_data['first_value_column']:
                b64_first_value_column = encode_attribute(self.cleaned_data['first_value_column'])
                attributes.append(f'first_value_column-{b64_first_value_column}')
            if self.cleaned_data['second_value_column']:
                b64_second_value_column = encode_attribute(self.cleaned_data['second_value_column'])
                attributes.append(f'second_value_column-{b64_second_value_column}')

        attributes.append(f'decimal_places-{self.cleaned_data.get("decimal_places", 0)}')
        if self.cleaned_data['show_table_totals']:
            attributes.append('show_totals-1')

    def save_number_fields(self, attributes):
        alignment = self.cleaned_data.get('alignment')
        attributes.append(f'alignment-{alignment}')
        if 'annotations_type' in self.cleaned_data and int(self.cleaned_data['annotations_type']) != 0:
            attributes.append(f'annotations_type-{self.cleaned_data["annotations_type"]}')
        elif 'append_annotation_query' in self.cleaned_data and self.cleaned_data['append_annotation_query']:
            attributes.append('append_annotation_query-1')
        if self.cleaned_data['annotation_column_id']:
            b64_annotation_column_id = encode_attribute(self.cleaned_data['annotation_column_id'])
            attributes.append(f'annotation_column_id-{b64_annotation_column_id}')
        if self.cleaned_data['show_table_totals']:
            attributes.append('show_totals-1')
        if self.cleaned_data['decimal_places'] > 0:
            attributes.append(f'decimal_places-{self.cleaned_data["decimal_places"]}')
        self.save_filter(attributes=attributes)

    def save_date_fields(self, attributes):
        if self.cleaned_data['annotations_value']:
            attributes.append(f'annotations_value-{self.cleaned_data["annotations_value"]}')
        if self.cleaned_data['date_format']:
            attributes.append(f'date_format-{self.cleaned_data["date_format"]}')

    def save_currency_fields(self, attributes):
        alignment = self.cleaned_data.get('alignment')
        attributes.append(f'alignment-{alignment}')
        if 'annotations_type' in self.cleaned_data and int(self.cleaned_data['annotations_type']) != 0:
            attributes.append(f'annotations_type-{self.cleaned_data["annotations_type"]}')
        elif 'append_annotation_query' in self.cleaned_data and self.cleaned_data['append_annotation_query']:
            attributes.append('append_annotation_query-1')
        if self.cleaned_data['annotation_column_id']:
            b64_annotation_column_id = encode_attribute(self.cleaned_data['annotation_column_id'])
            attributes.append(f'annotation_column_id-{b64_annotation_column_id}')
        if self.cleaned_data['show_table_totals']:
            attributes.append('show_totals-1')
        self.save_filter(attributes=attributes)

    def save_filter(self, attributes):
        if self.cleaned_data['has_filter']:
            attributes.append('has_filter-1')
            if self.cleaned_data['filter']:
                b64_filter = encode_attribute(self.cleaned_data['filter'])
                attributes.append(f'filter-{b64_filter}')
        if self.cleaned_data['multiple_columns']:
            attributes.append('multiple_columns-1')
            attributes.append(f'multiple_column_field-{self.cleaned_data["multiple_column_field"]}')

    def save_link_fields(self, attributes):
        if self.cleaned_data['link_css']:
            b64_link_css = encode_attribute(self.cleaned_data['link_css'])
            attributes.append(f'link_css-{b64_link_css}')
        if self.cleaned_data['link_html']:
            b64_link_html = encode_attribute(self.cleaned_data['link_html'])
            attributes.append(f'link_html-{b64_link_html}')
        if self.cleaned_data['is_icon'] and self.cleaned_data['is_icon']:
            attributes.append('is_icon-1')

    def save_reverse_foreign_key_str_fields(self, attributes):
        if int(self.cleaned_data['delimiter_type']) != 0:
            attributes.append(f'delimiter_type-{self.cleaned_data["delimiter_type"]}')
        if self.cleaned_data['has_filter']:
            attributes.append('has_filter-1')
            if self.cleaned_data['filter']:
                b64_filter = encode_attribute(self.cleaned_data['filter'])
                attributes.append(f'filter-{b64_filter}')

    def save_reverse_foreign_key_bool_fields(self, attributes):
        if int(self.cleaned_data['annotations_type']) != 0:
            attributes.append(f'annotations_type-{self.cleaned_data["annotations_type"]}')
        if self.cleaned_data['has_filter']:
            attributes.append('has_filter-1')
            if self.cleaned_data['filter']:
                b64_filter = encode_attribute(self.cleaned_data['filter'])
                attributes.append(f'filter-{b64_filter}')

    def save_reverse_foreign_key_choice_fields(self, attributes):
        if int(self.cleaned_data['delimiter_type']) != 0:
            attributes.append(f'delimiter_type-{self.cleaned_data["delimiter_type"]}')
        if self.cleaned_data['has_filter']:
            attributes.append('has_filter-1')
            if self.cleaned_data['filter']:
                b64_filter = encode_attribute(self.cleaned_data['filter'])
                attributes.append(f'filter-{b64_filter}')

    def save_reverse_foreign_key_date_fields(self, attributes):
        if int(self.cleaned_data['annotations_type']) != 0:
            attributes.append(f'annotations_type-{self.cleaned_data["annotations_type"]}')
        if int(self.cleaned_data['delimiter_type']) != 0:
            attributes.append(f'delimiter_type-{self.cleaned_data["delimiter_type"]}')
        if self.cleaned_data['date_format']:
            attributes.append(f'date_format-{self.cleaned_data["date_format"]}')
        if self.cleaned_data['has_filter']:
            attributes.append('has_filter-1')
            if self.cleaned_data['filter']:
                b64_filter = encode_attribute(self.cleaned_data['filter'])
                attributes.append(f'filter-{b64_filter}')

    def save_annotations_fields(self, attributes):
        if self.cleaned_data['show_table_totals']:
            attributes.append('show_totals-1')

    def get_additional_attributes(self):
        attributes = []
        data = json.loads(base64.b64decode(self.slug['data']))
        self.get_report_type_details()

        if self.cleaned_data['display_heading']:
            attributes.append('display_heading-1')
        else:
            attributes.append('display_heading-0')

        if self.django_field is not None and isinstance(self.django_field, DATE_FIELDS):
            self.save_date_fields(attributes=attributes)
        elif self.django_field is not None and isinstance(self.django_field, NUMBER_FIELDS):
            self.save_number_fields(attributes=attributes)
        elif isinstance(self.col_type_override, CURRENCY_COLUMNS):
            self.save_currency_fields(attributes=attributes)
        elif isinstance(self.col_type_override, LINK_COLUMNS):
            self.save_link_fields(attributes=attributes)
        elif isinstance(self.col_type_override, REVERSE_FOREIGN_KEY_STR_COLUMNS):
            self.save_reverse_foreign_key_str_fields(attributes=attributes)
        elif isinstance(self.col_type_override, REVERSE_FOREIGN_KEY_BOOL_COLUMNS):
            self.save_reverse_foreign_key_bool_fields(attributes=attributes)
        elif isinstance(self.col_type_override, REVERSE_FOREIGN_KEY_CHOICE_COLUMNS):
            self.save_reverse_foreign_key_choice_fields(attributes=attributes)
        elif isinstance(self.col_type_override, REVERSE_FOREIGN_KEY_DATE_COLUMNS):
            self.save_reverse_foreign_key_date_fields(attributes=attributes)
        elif self.col_type_override.annotations is not None:
            self.save_annotations_fields(attributes=attributes)
        elif self.is_mathematical_field(data=data):
            self.save_mathematical_fields(data=data, attributes=attributes)
        else:
            if self.cleaned_data['annotation_label'] and self.cleaned_data['annotation_label']:
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
    update_selection_command = 'update_selection'

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
        self.add_command({'function': self.update_selection_command})
        return self.command_response('close')

    def form_setup(self, form, *_args, **_kwargs):
        data = json.loads(base64.b64decode(self.slug['data']))
        report_builder_class, base_model = self.get_report_builder_class(report_type_id=self.slug['report_type_id'])
        django_field, col_type_override, _, _ = self.get_field_details(
            base_model=base_model,
            field=data['field'],
            report_builder_class=report_builder_class,
        )
        has_existing_annotations = col_type_override is not None and col_type_override.annotations is not None

        if django_field is not None and isinstance(django_field, NUMBER_FIELDS):
            return self.layout_number_field(form=form, has_existing_annotations=has_existing_annotations)
        elif isinstance(col_type_override, CURRENCY_COLUMNS):
            return self.layout_currency_field(form=form, has_existing_annotations=has_existing_annotations)

        elif isinstance(col_type_override, LINK_COLUMNS):
            return self.layout_link_field()
        elif isinstance(col_type_override, REVERSE_FOREIGN_KEY_STR_COLUMNS):
            return self.layout_reverse_foreign_key_str_field(form=form, col_type_override=col_type_override)

        elif isinstance(col_type_override, REVERSE_FOREIGN_KEY_BOOL_COLUMNS):
            return self.layout_reverse_foreign_key_bool_field(form=form, col_type_override=col_type_override)

        elif isinstance(col_type_override, REVERSE_FOREIGN_KEY_CHOICE_COLUMNS):
            return self.layout_reverse_foreign_key_choice_field(form=form, col_type_override=col_type_override)

        elif isinstance(col_type_override, REVERSE_FOREIGN_KEY_DATE_COLUMNS):
            self.layout_reverse_foreign_key_date_field(form=form, col_type_override=col_type_override)

        return None

    def layout_number_field(self, form, has_existing_annotations):
        if has_existing_annotations:
            annotations_type_field = 'append_annotation_query'
            form.add_trigger(
                'append_annotation_query',
                'onchange',
                [
                    {
                        'selector': '#annotations_fields_div',
                        'values': {'checked': 'show'},
                        'default': 'hide',
                    }
                ],
            )
        else:
            annotations_type_field = 'annotations_type'
            form.add_trigger(
                'annotations_type',
                'onchange',
                [
                    {
                        'selector': '#annotations_fields_div',
                        'values': {'0': 'hide'},
                        'default': 'show',
                    }
                ],
            )

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
            'display_heading',
            'show_table_totals',
            'decimal_places',
            'alignment',
            annotations_type_field,
            Div(
                'annotation_column_id',
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
                    css_id='filter_fields_div',
                ),
                FieldEx(
                    'multiple_columns',
                    template='django_modals/fields/label_checkbox.html',
                    field_class='col-6 input-group-sm',
                ),
                Div(
                    FieldEx('multiple_column_field'),
                    css_id='multiple_columns_fields_div',
                ),
                css_id='annotations_fields_div',
            ),
        ]

    def layout_currency_field(self, form, has_existing_annotations):
        if has_existing_annotations:
            annotations_type_field = 'append_annotation_query'
            form.add_trigger(
                'append_annotation_query',
                'onchange',
                [
                    {
                        'selector': '#annotations_fields_div',
                        'values': {'checked': 'show'},
                        'default': 'hide',
                    }
                ],
            )

        else:
            annotations_type_field = 'annotations_type'
            form.add_trigger(
                'annotations_type',
                'onchange',
                [
                    {
                        'selector': '#annotations_fields_div',
                        'values': {'0': 'hide'},
                        'default': 'show',
                    }
                ],
            )

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
            'display_heading',
            'show_table_totals',
            'alignment',
            annotations_type_field,
            Div(
                'annotation_column_id',
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
                    css_id='filter_fields_div',
                ),
                FieldEx(
                    'multiple_columns',
                    template='django_modals/fields/label_checkbox.html',
                    field_class='col-6 input-group-sm',
                ),
                Div(
                    FieldEx('multiple_column_field'),
                    css_id='multiple_columns_fields_div',
                ),
                css_id='annotations_fields_div',
            ),
        ]

    def layout_link_field(self):
        return ['title', 'display_heading', 'link_css', 'link_html', 'is_icon']

    def layout_reverse_foreign_key_str_field(self, form, col_type_override):
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

        return [
            'title',
            'display_heading',
            'delimiter_type',
            FieldEx(
                'has_filter',
                template='django_modals/fields/label_checkbox.html',
                field_class='col-6 input-group-sm',
            ),
            Div(
                FieldEx(
                    'filter',
                    template='advanced_report_builder/datatables/fields/single_query_builder.html',
                    extra_context={'report_builder_class_name': col_type_override.report_builder_class_name},
                ),
                css_id='filter_fields_div',
            ),
        ]

    def layout_reverse_foreign_key_bool_field(self, form, col_type_override):
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

        return [
            'title',
            'display_heading',
            'annotations_type',
            FieldEx(
                'has_filter',
                template='django_modals/fields/label_checkbox.html',
                field_class='col-6 input-group-sm',
            ),
            Div(
                FieldEx(
                    'filter',
                    template='advanced_report_builder/datatables/fields/single_query_builder.html',
                    extra_context={'report_builder_class_name': col_type_override.report_builder_class_name},
                ),
                css_id='filter_fields_div',
            ),
        ]

    def layout_reverse_foreign_key_choice_field(self, form, col_type_override):
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

        return [
            'title',
            'display_heading',
            'delimiter_type',
            FieldEx(
                'has_filter',
                template='django_modals/fields/label_checkbox.html',
                field_class='col-6 input-group-sm',
            ),
            Div(
                FieldEx(
                    'filter',
                    template='advanced_report_builder/datatables/fields/single_query_builder.html',
                    extra_context={'report_builder_class_name': col_type_override.report_builder_class_name},
                ),
                css_id='filter_fields_div',
            ),
        ]

    def layout_reverse_foreign_key_date_field(self, form, col_type_override):
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
            'annotations_type',
            'onchange',
            [
                {
                    'selector': '#div_id_delimiter_type',
                    'values': {f'{REVERSE_FOREIGN_KEY_ANNOTATION_DATE_ARRAY}': 'show'},
                    'default': 'hide',
                },
            ],
        )

        return [
            'title',
            'display_heading',
            'date_format',
            'annotations_type',
            'delimiter_type',
            FieldEx(
                'has_filter',
                template='django_modals/fields/label_checkbox.html',
                field_class='col-6 input-group-sm',
            ),
            Div(
                FieldEx(
                    'filter',
                    template='advanced_report_builder/datatables/fields/single_query_builder.html',
                    extra_context={'report_builder_class_name': col_type_override.report_builder_class_name},
                ),
                css_id='filter_fields_div',
            ),
        ]

    def ajax_get_query_builder_fields(self, **kwargs):
        field_auto_id = kwargs['field_auto_id']
        report_builder_class_name = kwargs.get('report_builder_class_name')

        if report_builder_class_name != '' and report_builder_class_name is not None:
            app_label, model, report_builder_fields_str = report_builder_class_name.split('.')
            new_model = apps.get_model(app_label, model)
            report_builder_class = get_report_builder_class(model=new_model, class_name=report_builder_fields_str)
            query_builder_filters = []
            self._get_query_builder_fields(
                base_model=new_model,
                query_builder_filters=query_builder_filters,
                report_builder_class=report_builder_class,
            )
        else:
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

        self.add_command(
            {
                'function': 'html',
                'selector': f'#{selector} span',
                'html': form.cleaned_data['title'],
            }
        )

        self.add_command({'function': 'update_pivot_selection'})
        return self.command_response('close')
