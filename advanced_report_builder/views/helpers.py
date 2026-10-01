from crispy_forms.bootstrap import StrictButton
from django.conf import settings
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


class BreakdownModalSizeMixin:
    """The size of a breakdown modal (the records behind a figure): ``xl`` unless the host asks otherwise.

    ``REPORT_BUILDER_BREAKDOWN_MODAL_SIZE`` sizes every breakdown (single value, bar chart, multi-value);
    ``breakdown_size_setting`` names a more specific setting a class reads first. The value becomes the
    dialog's ``modal-<size>`` class, so a host can ask for a size Bootstrap does not ship. A size given
    to ``as_view(size=...)``, which django-modals assigns in ``__init__``, still wins.
    """

    breakdown_size_setting = None
    _size_override = None

    @property
    def size(self):
        if self._size_override:
            return self._size_override
        if self.breakdown_size_setting:
            specific = getattr(settings, self.breakdown_size_setting, None)
            if specific:
                return specific
        return getattr(settings, 'REPORT_BUILDER_BREAKDOWN_MODAL_SIZE', 'xl')

    @size.setter
    def size(self, value):
        self._size_override = value
