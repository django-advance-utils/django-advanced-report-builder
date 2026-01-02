class TemplateTypes:
    output_type_templates = {
        'singlevaluereport': {'': {'advanced_report_builder/single_values/middle.html': {'name': 'Standard'}}},
        'barchartreport': {'': {'advanced_report_builder/charts/bar/middle.html': {'name': 'Standard'}}},
        'linechartreport': {'': {'advanced_report_builder/charts/line/middle.html': {'name': 'Standard'}}},
        'piechartreport': {'': {'advanced_report_builder/charts/pie/middle.html': {'name': 'Standard'}}},
        'funnelchartreport': {'': {'advanced_report_builder/charts/funnel/middle.html': {'name': 'Standard'}}},
        'kanbanreport': {'': {'advanced_report_builder/kanban/middle.html': {'name': 'Standard'}}},
        'calendarreport': {'': {'advanced_report_builder/calendar/middle.html': {'name': 'Standard'}}},
        'multivaluereport': {'': {'advanced_report_builder/multi_values/middle.html': {'name': 'Standard'}}},
    }

    def get_template_name_from_instance_type(self, instance_type):
        templates = self.output_type_templates.get(instance_type)
        template = templates.get('')
        return template