from django.forms.widgets import TextInput
from django.urls import NoReverseMatch, reverse
from django_modals.fields import FieldEx


class DataMergeWidget(TextInput):
    template_name = 'advanced_report_builder/data_merge/data_merge.html'
    crispy_field_class = FieldEx
    input_type = 'textarea'
    crispy_kwargs = {
        'label_class': 'col-3 col-form-label-sm',
        'field_class': 'col-12 input-group-sm',
    }

    def __init__(self, data_merge_data=None, height=150, *args, **kwargs):
        self.height = height
        super().__init__(*args, **kwargs)
        self.data_merge_data = data_merge_data

    def get_context(self, name, value, attrs=None):
        context = super().get_context(name, value, attrs)
        if context['widget']['value'] is None:
            context['widget']['value'] = ''
        if self.data_merge_data is None:
            context['data_merge'] = None
        else:
            context['data_merge'] = self.data_merge_data.build_menus()

        context['disabled'] = attrs is not None and attrs.get('disabled', False)
        context['height'] = self.height
        # django-modals URLs for the If-Statement Generator and Save-as-include dialogs, with the
        # editor's field id baked into the slug so the modal can target this editor on submit.
        # Optional (reverse guarded) so the widget still works when the host project hasn't
        # wired the endpoints.
        field_auto_id = context['widget']['attrs'].get('id', '')
        slug = {'slug': f'field_auto_id-{field_auto_id}'}
        try:
            context['if_statement_url'] = reverse('settings_client:data_merge_if_statement_modal', kwargs=slug)
            context['save_include_url'] = reverse('settings_client:data_merge_save_include_modal', kwargs=slug)
        except NoReverseMatch:
            context['if_statement_url'] = None
            context['save_include_url'] = None
        return context
