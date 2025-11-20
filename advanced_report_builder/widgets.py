from django.forms import TextInput


class SmallNumberInputWidget(TextInput):
    crispy_kwargs = {'field_class': 'col-2', 'input_size': 'input-group-sm'}
