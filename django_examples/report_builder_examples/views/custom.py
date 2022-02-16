from django.views.generic import TemplateView


class Custom1(TemplateView):
    use_annotations = False
    template_name = 'report_builder_examples/custom1.html'

    def __init__(self, **kwargs):
        self.report = None
        super().__init__(**kwargs)

    def dispatch(self, request, *args, **kwargs):
        self.report = kwargs.get('report')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['report'] = self.report
        return context
