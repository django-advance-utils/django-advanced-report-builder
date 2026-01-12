from crispy_forms.layout import HTML, Div
from django.conf import settings
from django.forms import CharField
from django.urls import reverse
from django_datatables.columns import MenuColumn
from django_datatables.widgets import DataTableWidget
from django_menus.menu import HtmlMenu, MenuItem
from django_modals.modals import ModelFormModal
from django_modals.processes import PERMISSION_OFF, PROCESS_EDIT_DELETE

from advanced_report_builder.columns import ColourColumn
from advanced_report_builder.form_utils import PercentageWidget, SmallInputWidget
from advanced_report_builder.models import Target, TargetColour
from advanced_report_builder.utils import get_query_js


class TargetModal(ModelFormModal):
    model = Target
    form_fields = ['name', 'target_type', 'period_type', 'default_colour', 'default_value', 'default_percentage']

    widgets = {'default_value': SmallInputWidget, 'default_percentage': PercentageWidget}
    process = PROCESS_EDIT_DELETE
    permission_delete = PERMISSION_OFF

    def form_setup(self, form, *_args, **_kwargs):
        fields = ['name', 'target_type', 'period_type', 'default_colour', 'default_value', 'default_percentage']

        form.add_trigger(
            'target_type',
            'onchange',
            [
                {
                    'selector': '#div_id_default_value',
                    'values': {Target.TargetType.COUNT: 'show', Target.TargetType.MONEY: 'show'},
                    'default': 'hide',
                },
                {
                    'selector': '#div_id_default_percentage',
                    'values': {Target.TargetType.PERCENTAGE: 'show'},
                    'default': 'hide',
                },
            ],
        )

        if self.object.id:
            self.add_target_colours(form=form, fields=fields)
        return fields

    def post_save(self, created, form):
        if created:
            url_name = getattr(settings, 'REPORT_BUILDER_TARGET_URL_NAME', '')
            if url_name:
                url = reverse(url_name, kwargs={'slug': self.object.slug})
                self.add_command('redirect', url=url)

    def add_target_colours(self, form, fields):
        add_query_js = 'django_modal.process_commands_lock([{"function": "post_modal", "button": {"button": "add_target_colour"}}])'

        description_add_menu_items = [
            MenuItem(
                add_query_js.replace('"', '&quot;'),
                menu_display='Add Colour Override',
                css_classes='btn btn-primary',
                font_awesome='fas fa-palette',
                link_type=MenuItem.HREF,
            )
        ]

        menu = HtmlMenu(self.request, 'advanced_report_builder/datatables/onclick_menu.html').add_items(
            *description_add_menu_items
        )
        fields.append(Div(HTML(menu.render()), css_class='form-buttons'))
        target_colour_menu = self.query_target_colour_menu()

        form.fields['target_colours'] = CharField(
            required=False,
            label='Colour Overrides',
            widget=DataTableWidget(
                model=TargetColour,
                fields=[
                    '_.index',
                    '.id',
                    'percentage',
                    ColourColumn(column_name='colour', field='colour'),
                    MenuColumn(
                        column_name='menu',
                        field='id',
                        column_defs={'orderable': False, 'className': 'dt-right'},
                        menu=HtmlMenu(
                            self.request,
                            'advanced_report_builder/datatables/onclick_menu.html',
                        ).add_items(*target_colour_menu),
                    ),
                ],
                attrs={'filter': {'target__id': self.object.id}},
            ),
        )
        fields.append('target_colours')

    @staticmethod
    def query_target_colour_menu():
        edit_query_js = get_query_js('edit_target_colour', 'target_colour_id')

        description_edit_menu_items = [
            MenuItem(
                edit_query_js.replace('"', '&quot;'),
                menu_display='Edit',
                css_classes='btn btn-sm btn-outline-dark',
                font_awesome='fas fa-pencil',
                link_type=MenuItem.HREF,
            ),
        ]
        return description_edit_menu_items

    def button_add_target_colour(self, **_kwargs):
        slug = f'target_id-{self.object.id}'
        url = reverse(
            'advanced_report_builder:target_colour_modal',
            kwargs={'slug': slug},
        )
        return self.command_response('show_modal', modal=url)

    def button_edit_target_colour(self, **_kwargs):
        target_colour_id = _kwargs['target_colour_id'][1:]
        slug = f'pk-{target_colour_id}'
        url = reverse(
            'advanced_report_builder:target_colour_modal',
            kwargs={'slug': slug},
        )
        return self.command_response('show_modal', modal=url)


class TargetColourModal(ModelFormModal):
    model = TargetColour
    form_fields = ['colour', 'percentage']
    widgets = {'percentage': PercentageWidget}

    process = PROCESS_EDIT_DELETE
    permission_delete = PERMISSION_OFF
