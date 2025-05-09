from crispy_forms.bootstrap import StrictButton
from django_modals.forms import CrispyForm, ModelCrispyForm


class QueryBuilderModelForm(ModelCrispyForm):
    def submit_button(self, css_class='btn-success modal-submit', button_text='Submit', **kwargs):
        return StrictButton(
            button_text,
            onclick=f'save_modal_{self.form_id}()',
            css_class=css_class,
            **kwargs,
        )


class QueryBuilderForm(CrispyForm):
    def submit_button(self, css_class='btn-success modal-submit', button_text='Submit', **kwargs):
        return StrictButton(
            button_text,
            onclick=f'save_modal_{self.form_id}()',
            css_class=css_class,
            **kwargs,
        )
