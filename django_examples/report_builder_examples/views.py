import datetime
from io import BytesIO

from django import forms
from django.http import HttpResponse
from django.views.generic import TemplateView
from django.urls import reverse
from openpyxl import Workbook

from ajax_helpers.mixins import AjaxHelpers, ReceiveForm, AjaxFileHelpers
from django_menus.menu import MenuMixin
# from show_src_code.view_mixins import DemoViewMixin


class MainMenu(MenuMixin):

    def setup_menu(self):
        super().setup_menu()
        self.add_menu('main_menu').add_items('ajax_main')


class TestForm(forms.Form):
    text_entry = forms.CharField(max_length=100)


class ToolTip(TemplateView):
    template_name = 'ajax_examples/tooltip_template.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.GET['django'] == 'today':
            context['time'] = datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')
            context['day'] = 'Today'
        else:
            context['time'] = (datetime.datetime.now()-datetime.timedelta(days=1)).strftime('%m/%d/%Y, %H:%M:%S')
            context['day'] = 'Yesterday'
        return context


class Example1(MainMenu, AjaxFileHelpers, ReceiveForm, AjaxHelpers, TemplateView):

    template_name = 'ajax_examples/base.html'

    def button_redirect(self, **kwargs):
        self.add_command('message', text='Will redirect after this message')
        self.add_command('redirect', url=reverse('redirect'))
        return self.command_response()

    def button_test_ajax(self, **kwargs):
        return self.command_response('message', text='From Django View')

    def button_test_html(self, **kwargs):
        return self.command_response('html', selector='#html_test', html='From Django View')

    def form_form_id(self, **kwargs):
        return self.command_response('message', text=f'From Django View - field {kwargs["field1"]}')

    def form_django_form_id(self, **kwargs):
        a = TestForm(kwargs)
        if a.is_valid():
            return self.command_response('html', selector='#django_form_id', html='thank you', parent=True)
        else:
            return self.command_response('html', selector='#django_form_id', html=a.as_p())

    @staticmethod
    def button_download_text(**kwargs):
        response = HttpResponse(content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename="text.txt"'
        response.write('text file data')
        return response

    @staticmethod
    def button_download_blob(**kwargs):
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(['hello', 'world'])
        filename = 'test.xlsx'
        output = BytesIO()
        workbook.save(output)
        output.seek(0)
        response = HttpResponse(content_type='application/ms-excel')
        # Providing extra download information for the user's browser.
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename
        response.write(output.read())
        return response

    def button_download_base64(self, **kwargs):
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(['hello', 'world'])
        filename = 'test_base64.xlsx'
        output = BytesIO()
        workbook.save(output)
        output.seek(0)
        import base64
        return self.command_response('save_file', data=base64.b64encode(output.read()).decode('ascii'),
                                     filename=filename)

    def file_upload(self, file):
        return self.command_response('message', text=f'Received {file.name} size {file.size}')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = TestForm()
        return context

    def add_to_context(self, **kwargs):
        return {'title': type(self).__name__, 'filter': filter}

    def timer_demo_interval(self, **_kwargs):
        return self.command_response('html', selector='#time_div',
                                     html=datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S'))


class Example2(Example1):

    template_name = 'ajax_examples/redirect.html'
