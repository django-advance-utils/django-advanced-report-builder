class TemplateTypes:
    output_type_templates = {
        'singlevaluereport': {
            '': {'template': 'advanced_report_builder/single_values/middle.html', 'name': 'Standard'},
            'gauge': {'template': 'advanced_report_builder/single_values/gauge_middle.html', 'name': 'Gauge'},
        },
        'barchartreport': {'': {'template': 'advanced_report_builder/charts/bar/middle.html', 'name': 'Standard'}},
        'linechartreport': {'': {'template': 'advanced_report_builder/charts/line/middle.html', 'name': 'Standard'}},
        'piechartreport': {'': {'template': 'advanced_report_builder/charts/pie/middle.html', 'name': 'Standard'}},
        'funnelchartreport': {
            '': {'template': 'advanced_report_builder/charts/funnel/middle.html', 'name': 'Standard'}
        },
        'kanbanreport': {'': {'template': 'advanced_report_builder/kanban/middle.html', 'name': 'Standard'}},
        'calendarreport': {'': {'template': 'advanced_report_builder/calendar/middle.html', 'name': 'Standard'}},
        'multivaluereport': {'': {'template': 'advanced_report_builder/multi_values/middle.html', 'name': 'Standard'}},
    }

    def get_template_name_from_instance_type(self, instance_type, template_style=''):
        templates_data = self.output_type_templates.get(instance_type)
        if templates_data is None:
            return None
        template_data = templates_data.get(template_style) or templates_data.get('')
        if template_data is None:
            return None
        return template_data['template']

    def get_template_style_choices(self, instance_type):
        templates_data = self.output_type_templates.get(instance_type)
        if templates_data is None:
            return []
        templates_choices = []
        for code, template_data in templates_data.items():
            templates_choices.append((code, template_data['name']))
        return templates_choices
