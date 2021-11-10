import base64
import json

from django.forms import CharField, ChoiceField
from django.shortcuts import get_object_or_404
from django_datatables.datatables import ColumnInitialisor
from django_modals.forms import CrispyForm

from report_builder.globals import DATE_FIELDS, NUMBER_FIELDS, ANNOTATION_VALUE_CHOICES, ANNOTATIONS_CHOICES, \
    DATE_FORMAT_TYPES
from report_builder.models import ReportType


from report_builder.utils import split_attr


class FieldForm(CrispyForm):

    def get_django_field(self):
        data = json.loads(base64.b64decode(self.slug['data']))
        report_type = get_object_or_404(ReportType, pk=self.slug['report_type_id'])
        base_model = report_type.content_type.model_class()

        column_initialisor = ColumnInitialisor(start_model=base_model, path=data['field'])
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
                if data_attr and 'annotations_value' in data_attr:
                    self.fields['annotations_value'].initial = data_attr['annotations_value']

                self.fields['date_format'] = ChoiceField(choices=DATE_FORMAT_TYPES, required=False)
                if data_attr and 'date_format' in data_attr:
                    self.fields['date_format'].initial = data_attr['date_format']

            elif isinstance(django_field, NUMBER_FIELDS):
                self.fields['annotations_type'] = ChoiceField(choices=ANNOTATIONS_CHOICES, required=False)
                if data_attr and 'annotations_type' in data_attr:
                    self.fields['annotations_type'].initial = data_attr['annotations_type']
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

            elif (isinstance(django_field, NUMBER_FIELDS) and
                    self.cleaned_data['annotations_type']):
                attributes.append(f'annotations_type-{self.cleaned_data["annotations_type"]}')

        if attributes:
            return '-'.join(attributes)

        return None
