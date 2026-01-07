from django.forms import TextInput
from django_modals.fields import FieldEx


class PercentageWidget(TextInput):
    crispy_kwargs = {'appended_text': '%', 'field_class': 'col-sm-3', 'input_size': 'input-group-sm'}
    crispy_field_class = FieldEx


class SmallInputWidget(TextInput):
    crispy_kwargs = {'field_class': 'col-sm-3', 'input_size': 'input-group-sm'}
    crispy_field_class = FieldEx
