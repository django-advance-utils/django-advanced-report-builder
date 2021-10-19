import base64
import json

from django.forms import CharField
from django_modals.forms import CrispyForm


class FieldForm(CrispyForm):

    def setup_modal(self, *args, **kwargs):
        data = json.loads(base64.b64decode(self.slug['data']))
        self.fields['title'] = CharField(initial=data['title'])
        super().setup_modal(*args, **kwargs)

