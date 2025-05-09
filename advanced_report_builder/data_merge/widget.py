from django.forms.widgets import Input


class DataMergeWidget(Input):
    template_name = 'advanced_report_builder/data_merge/data_merge.html'
    input_type = 'textarea'
    crispy_kwargs = {
        'label_class': 'col-3 col-form-label-sm',
        'field_class': 'col-12 input-group-sm',
    }

    def __init__(self, data_merge_data=None, height=150):
        self.height = height
        super().__init__()
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
        return context
