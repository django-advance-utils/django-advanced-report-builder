import json

from django_modals.fields import FieldEx
from django_modals.form_helpers import HorizontalNoEnterHelper
from django_modals.modals import ModelFormModal
from django_modals.processes import PROCESS_EDIT_DELETE, PERMISSION_OFF

from advanced_report_builder.models import ReportQuery
from advanced_report_builder.views.datatables.modal import TableQueryForm
from advanced_report_builder.views.modals_base import QueryBuilderModalBaseMixin


class QueryModal(QueryBuilderModalBaseMixin, ModelFormModal):
    model = ReportQuery
    process = PROCESS_EDIT_DELETE
    permission_delete = PERMISSION_OFF
    form_class = TableQueryForm
    helper_class = HorizontalNoEnterHelper

    template_name = 'advanced_report_builder/query_modal.html'
    no_header_x = True

    def post_save(self, created, form):
        self.add_command({'function': 'save_query_builder_id_query'})
        return self.command_response('close')

    def form_setup(self, form, *_args, **_kwargs):
        fields = ['name',
                  FieldEx('query', template='advanced_report_builder/query_builder.html')]
        return fields

    def ajax_get_query_builder_fields(self, **kwargs):
        field_auto_id = kwargs['field_auto_id']

        report_type_id = self.slug['report_type']
        query_builder_filters = self.get_query_builder_report_type_field(report_type_id=report_type_id)

        return self.command_response(f'query_builder_{field_auto_id}', data=json.dumps(query_builder_filters))
