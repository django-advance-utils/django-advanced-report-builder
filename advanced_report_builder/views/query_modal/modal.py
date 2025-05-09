import json

from crispy_forms.layout import HTML, Div
from django.forms import CharField
from django.urls import reverse
from django_datatables.columns import ColumnBase, MenuColumn
from django_datatables.widgets import DataTableReorderWidget
from django_menus.menu import HtmlMenu, MenuItem
from django_modals.fields import FieldEx
from django_modals.form_helpers import HorizontalNoEnterHelper
from django_modals.forms import ModelCrispyForm
from django_modals.modals import ModelFormModal
from django_modals.processes import PERMISSION_OFF, PROCESS_EDIT_DELETE

from advanced_report_builder.models import ReportQuery, ReportQueryOrder, ReportType
from advanced_report_builder.toggle import RBToggle
from advanced_report_builder.utils import get_query_js
from advanced_report_builder.views.helpers import QueryBuilderModelForm
from advanced_report_builder.views.modals_base import QueryBuilderModalBaseMixin


class QueryForm(QueryBuilderModelForm):
    cancel_class = 'btn-secondary modal-cancel'

    class Meta:
        model = ReportQuery
        fields = ['name', 'query']


class QueryModal(QueryBuilderModalBaseMixin, ModelFormModal):
    model = ReportQuery
    process = PROCESS_EDIT_DELETE
    permission_delete = PERMISSION_OFF
    form_class = QueryForm
    helper_class = HorizontalNoEnterHelper
    ajax_commands = ['datatable', 'button']

    template_name = 'advanced_report_builder/query_modal.html'
    no_header_x = True

    def __init__(self, *args, **kwargs):
        self._base_and_class = None
        super().__init__(*args, **kwargs)

    def post_save(self, created, form):
        self.add_command({'function': 'save_query_builder_id_query'})
        return self.command_response('close')

    def form_setup(self, form, *_args, **_kwargs):
        fields = [
            'name',
            FieldEx('query', template='advanced_report_builder/query_builder.html'),
        ]

        if self.object.id and self.slug.get('show_order_by') == '1':
            self.add_query_orders(form=form, fields=fields)

        return fields

    def ajax_get_query_builder_fields(self, **kwargs):
        field_auto_id = kwargs['field_auto_id']
        report_type_id = self.slug['report_type']
        query_builder_filters = self.get_query_builder_report_type_field(report_type_id=report_type_id)
        return self.command_response(f'query_builder_{field_auto_id}', data=json.dumps(query_builder_filters))

    def get_report_builder_base_and_class(self):
        if self._base_and_class is None:
            self._base_and_class = self.get_report_builder_class(report_type_id=self.slug['report_type'])
        return self._base_and_class

    def order_by_result(self, _column, data_dict, _page_results):
        order_by_field = data_dict['order_by_field']
        field_values = []
        report_builder_class, base_model = self.get_report_builder_base_and_class()
        self.get_field_display_value(
            field_type='order',
            fields_values=field_values,
            base_model=base_model,
            report_builder_class=report_builder_class,
            selected_field_value=order_by_field,
        )

        if len(field_values) > 0:
            return field_values[0]['label']

        return order_by_field

    def add_query_orders(self, form, fields):
        add_query_js = (
            'django_modal.process_commands_lock([{"function": "post_modal", "button": {"button": "add_query_order"}}])'
        )

        description_add_menu_items = [
            MenuItem(
                add_query_js.replace('"', '&quot;'),
                menu_display='Add Order by',
                css_classes='btn btn-primary',
                font_awesome='fas fa-pencil',
                link_type=MenuItem.HREF,
            )
        ]

        menu = HtmlMenu(self.request, 'advanced_report_builder/datatables/onclick_menu.html').add_items(
            *description_add_menu_items
        )

        fields.append(Div(HTML(menu.render()), css_class='form-buttons'))
        edit_query_js = get_query_js('edit_query_order', 'query_order_id')
        duplicate_query_js = get_query_js('duplicate_query_order', 'query_order_id')
        description_edit_menu_items = [
            MenuItem(
                duplicate_query_js.replace('"', '&quot;'),
                menu_display='Duplicate',
                css_classes='btn btn-sm btn-outline-dark',
                font_awesome='fas fa-clone',
                link_type=MenuItem.HREF,
            ),
            MenuItem(
                edit_query_js.replace('"', '&quot;'),
                menu_display='Edit',
                css_classes='btn btn-sm btn-outline-dark btn-query-edit',
                font_awesome='fas fa-pencil',
                link_type=MenuItem.HREF,
            ),
        ]

        template = 'advanced_report_builder/datatables/onclick_menu.html'
        form.fields['orders'] = CharField(
            required=False,
            label='Query Order',
            widget=DataTableReorderWidget(
                model=ReportQueryOrder,
                order_field='order',
                fields=[
                    '_.index',
                    '.id',
                    ColumnBase(
                        column_name='order_by',
                        field='order_by_field',
                        row_result=self.order_by_result,
                    ),
                    'order_by_ascending',
                    MenuColumn(
                        column_name='menu',
                        field='id',
                        column_defs={'orderable': False, 'className': 'dt-right'},
                        menu=HtmlMenu(self.request, template).add_items(*description_edit_menu_items),
                    ),
                ],
                attrs={'filter': {'report_query__id': self.object.id}},
            ),
        )
        fields.append('orders')

    def get_report_type(self):
        return self.slug['report_type']

    def button_duplicate_query_order(self, **_kwargs):
        query_id = _kwargs['query_order_id'][1:]
        report_query_order = ReportQueryOrder.objects.get(pk=query_id)
        report_query_order.slug = None
        report_query_order.pk = None
        report_query_order.order = None
        report_query_order.save()

        report_type = self.get_report_type()
        url = reverse(
            'advanced_report_builder:query_order_modal',
            kwargs={'slug': f'pk-{report_query_order.id}-report_type-{report_type}'},
        )
        return self.command_response('show_modal', modal=url)

    def button_add_query_order(self, **_kwargs):
        report_type = self.get_report_type()
        url = reverse(
            'advanced_report_builder:query_order_modal',
            kwargs={'slug': f'report_query_id-{self.object.id}-report_type-{report_type}'},
        )
        return self.command_response('show_modal', modal=url)

    def button_edit_query_order(self, **_kwargs):
        query_order_id = _kwargs['query_order_id'][1:]
        report_type = self.get_report_type()
        url = reverse(
            'advanced_report_builder:query_order_modal',
            kwargs={'slug': f'pk-{query_order_id}-report_type-{report_type}'},
        )
        return self.command_response('show_modal', modal=url)

    def datatable_sort(self, **kwargs):
        current_sort = dict(ReportQueryOrder.objects.filter(report_query=self.object.id).values_list('id', 'order'))
        for s in kwargs['sort']:
            if current_sort[s[1]] != s[0]:
                o = ReportQueryOrder.objects.get(id=s[1])
                o.order = s[0]
                o.save()
        return self.command_response('')

    def form_valid(self, form):
        org_id = self.object.pk if hasattr(self, 'object') else None
        instance = form.save(commit=False)
        instance._current_user = self.request.user
        instance.save()
        self.post_save(created=org_id is None, form=form)
        if not self.response_commands:
            self.add_command('reload')
        return self.command_response()


class OrderByFieldForm(ModelCrispyForm):
    class Meta:
        model = ReportQueryOrder
        fields = ['order_by_field', 'order_by_ascending']

    cancel_class = 'btn-secondary modal-cancel'

    def cancel_button(self, css_class=cancel_class, **kwargs):
        commands = [{'function': 'save_query_builder_id_query'}, {'function': 'close'}]
        return self.button('Cancel', commands, css_class, **kwargs)


class QueryOrderModal(QueryBuilderModalBaseMixin, ModelFormModal):
    form_class = OrderByFieldForm
    ajax_commands = ['datatable', 'button']
    model = ReportQueryOrder
    process = PROCESS_EDIT_DELETE
    permission_delete = PERMISSION_OFF
    helper_class = HorizontalNoEnterHelper
    no_header_x = True

    def form_setup(self, form, *_args, **_kwargs):
        form.fields['order_by_ascending'].widget = RBToggle()

        report_type = ReportType.objects.get(id=self.slug['report_type'])
        order_by_field = _kwargs['data'].get('order_by_field') if 'data' in _kwargs else form.instance.order_by_field

        self.setup_field(
            field_type='order',
            form=form,
            field_name='order_by_field',
            selected_field_id=order_by_field,
            report_type=report_type,
        )

    def select2_order_by_field(self, **kwargs):
        return self.get_fields_for_select2(
            field_type='django_order',
            report_type=self.slug['report_type'],
            search_string=kwargs.get('search'),
        )

    def post_save(self, created, form):
        self.add_command({'function': 'save_query_builder_id_query'})
        return self.command_response('close')
