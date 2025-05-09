from crispy_forms.layout import HTML, Div
from django.conf import settings
from django.forms import CharField
from django.urls import reverse
from django_datatables.columns import MenuColumn
from django_datatables.widgets import DataTableReorderWidget
from django_menus.menu import HtmlMenu, MenuItem

from advanced_report_builder.models import ReportQuery
from advanced_report_builder.utils import get_query_js


class MultiQueryModalMixin:
    show_order_by = True

    ajax_commands = ['datatable', 'button', 'ajax']

    def datatable_sort(self, **kwargs):
        form = self.get_form()
        widget = form.fields[kwargs['table_id'][3:]].widget
        _model = widget.attrs['table_model']
        current_sort = dict(_model.objects.filter(report_id=self.object.id).values_list('id', 'order'))
        for s in kwargs['sort']:
            if current_sort[s[1]] != s[0]:
                o = _model.objects.get(id=s[1])
                o.order = s[0]
                o.save()
        return self.command_response('null')

    def get_report_type(self, **_kwargs):
        return _kwargs['report_type']

    def button_duplicate_query(self, **_kwargs):
        query_id = _kwargs['query_id'][1:]
        report_query = ReportQuery.objects.get(pk=query_id)
        report_query_orders = report_query.reportqueryorder_set.all()
        report_query.slug = None
        report_query.pk = None
        report_query.order = None
        report_query.save()

        for report_query_order in report_query_orders:
            report_query_order.pk = None
            report_query_order.report_query = report_query
            report_query_order.save()

        report_type = self.get_report_type(**_kwargs)
        url = reverse(
            'advanced_report_builder:query_modal',
            kwargs={'slug': f'pk-{report_query.id}-report_type-{report_type}'},
        )
        return self.command_response('show_modal', modal=url)

    def button_add_query(self, **_kwargs):
        report_type = self.get_report_type(**_kwargs)
        show_order_by = 1 if self.show_order_by else 0
        url = reverse(
            'advanced_report_builder:query_modal',
            kwargs={'slug': f'report_id-{self.object.id}-report_type-{report_type}-show_order_by-{show_order_by}'},
        )
        return self.command_response('show_modal', modal=url)

    def button_edit_query(self, **_kwargs):
        query_id = _kwargs['query_id'][1:]
        report_type = self.get_report_type(**_kwargs)
        show_order_by = 1 if self.show_order_by else 0
        url = reverse(
            'advanced_report_builder:query_modal',
            kwargs={'slug': f'pk-{query_id}-report_type-{report_type}-show_order_by-{show_order_by}'},
        )
        return self.command_response('show_modal', modal=url)

    def query_menu(self):
        edit_query_js = get_query_js('edit_query', 'query_id')
        duplicate_query_js = get_query_js('duplicate_query', 'query_id')

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
                css_classes='btn btn-sm btn-outline-dark',
                font_awesome='fas fa-pencil',
                link_type=MenuItem.HREF,
            ),
        ]
        return description_edit_menu_items

    def add_extra_queries(self, form, fields):
        add_query_js = (
            'django_modal.process_commands_lock([{"function": "post_modal", "button": {"button": "add_query"}}])'
        )

        description_add_menu_items = [
            MenuItem(
                add_query_js.replace('"', '&quot;'),
                menu_display='Add Query Version',
                css_classes='btn btn-primary',
                font_awesome='fas fa-pencil',
                link_type=MenuItem.HREF,
            )
        ]

        menu = HtmlMenu(self.request, 'advanced_report_builder/datatables/onclick_menu.html').add_items(
            *description_add_menu_items
        )

        fields.append(Div(HTML(menu.render()), css_class='form-buttons'))
        description_edit_menu_items = self.query_menu()

        form.fields['queries'] = CharField(
            required=False,
            label='Queries Versions',
            widget=DataTableReorderWidget(
                model=ReportQuery,
                order_field='order',
                fields=[
                    '_.index',
                    '.id',
                    'name',
                    MenuColumn(
                        column_name='menu',
                        field='id',
                        column_defs={'orderable': False, 'className': 'dt-right'},
                        menu=HtmlMenu(
                            self.request,
                            'advanced_report_builder/datatables/onclick_menu.html',
                        ).add_items(*description_edit_menu_items),
                    ),
                ],
                attrs={'filter': {'report__id': self.object.id}},
            ),
        )
        fields.append('queries')

    def post_save(self, created, form):
        if created:
            self.modal_redirect(
                self.request.resolver_match.view_name,
                slug=f'pk-{self.object.id}-new-True',
            )
        else:
            url_name = getattr(settings, 'REPORT_BUILDER_DETAIL_URL_NAME', '')
            if url_name and self.slug.get('new'):
                url = reverse(url_name, kwargs={'slug': self.object.slug})
                self.command_response('redirect', url=url)
