import base64
import json

from django.forms import CharField, ChoiceField, BooleanField, IntegerField
from django.shortcuts import get_object_or_404
from django_datatables.datatables import ColumnInitialisor
from django_modals.forms import CrispyForm
from django_modals.widgets.widgets import Toggle

from advanced_report_builder.globals import DATE_FIELDS, NUMBER_FIELDS, ANNOTATION_VALUE_CHOICES, ANNOTATIONS_CHOICES, \
    DATE_FORMAT_TYPES
from advanced_report_builder.models import ReportType


from advanced_report_builder.utils import split_attr


class FieldForm(CrispyForm):

    def get_django_field(self):
        data = json.loads(base64.b64decode(self.slug['data']))
        report_type = get_object_or_404(ReportType, pk=self.slug['report_type_id'])
        base_model = report_type.content_type.model_class()

        column_initialisor = ColumnInitialisor(start_model=base_model, path=data['field'])
        cols = column_initialisor.get_columns()

        if column_initialisor.django_field is None and cols:
            column_initialisor = ColumnInitialisor(start_model=base_model, path=cols[0].field)
            column_initialisor.get_columns()

        return column_initialisor.django_field

    def setup_modal(self, *args, **kwargs):
        data = json.loads(base64.b64decode(self.slug['data']))
        django_field = self.get_django_field()

        self.fields['title'] = CharField(initial=data['title'])

        if django_field is not None:
            data_attr = split_attr(data)

            if isinstance(django_field, DATE_FIELDS):

                self.fields['annotations_value'] = ChoiceField(choices=ANNOTATION_VALUE_CHOICES, required=False)
                if 'annotations_value' in data_attr:
                    self.fields['annotations_value'].initial = data_attr['annotations_value']

                self.fields['date_format'] = ChoiceField(choices=DATE_FORMAT_TYPES, required=False)
                if 'date_format' in data_attr:
                    self.fields['date_format'].initial = data_attr['date_format']

            elif isinstance(django_field, NUMBER_FIELDS):
                self.fields['annotations_type'] = ChoiceField(choices=ANNOTATIONS_CHOICES, required=False)
                if 'annotations_type' in data_attr:
                    self.fields['annotations_type'].initial = data_attr['annotations_type']

                self.fields['show_totals'] = BooleanField(required=False,
                                                          widget=Toggle(attrs={'data-onstyle': 'success',
                                                                               'data-on': 'YES',
                                                                               'data-off': 'NO'}))
                if 'show_totals' in data_attr and data_attr['show_totals'] == '1':
                    self.fields['show_totals'].initial = True

                self.fields['decimal_places'] = IntegerField()
                self.fields['decimal_places'].initial = int(data_attr.get('decimal_places', 0))

        super().setup_modal(*args, **kwargs)

    def get_additional_attributes(self):
        attributes = []
        django_field = self.get_django_field()
        if django_field is not None:
            if isinstance(django_field, DATE_FIELDS):
                if self.cleaned_data['annotations_value']:
                    attributes.append(f'annotations_value-{self.cleaned_data["annotations_value"]}')
                if self.cleaned_data['date_format']:
                    attributes.append(f'date_format-{self.cleaned_data["date_format"]}')

            elif isinstance(django_field, NUMBER_FIELDS):
                if self.cleaned_data['annotations_type']:
                    attributes.append(f'annotations_type-{self.cleaned_data["annotations_type"]}')
                if self.cleaned_data['show_totals'] and self.cleaned_data["show_totals"]:
                    attributes.append('show_totals-1')
                if self.cleaned_data['decimal_places'] > 0:
                    attributes.append(f'decimal_places-{self.cleaned_data["decimal_places"]}')

        if attributes:
            return '-'.join(attributes)

        return None
