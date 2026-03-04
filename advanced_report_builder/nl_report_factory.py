from advanced_report_builder.models import (
    BarChartReport,
    FunnelChartReport,
    LineChartReport,
    PieChartReport,
    ReportQuery,
    SingleValueReport,
    TableReport,
)


class NLReportFactory:
    def create_report(self, config, report_type, output_type, user=None):
        creators = {
            'table': self._create_table_report,
            'bar_chart': self._create_bar_chart_report,
            'line_chart': self._create_line_chart_report,
            'pie_chart': self._create_pie_chart_report,
            'single_value': self._create_single_value_report,
            'funnel_chart': self._create_funnel_chart_report,
        }
        creator = creators.get(output_type)
        if creator is None:
            raise ValueError(f'Unsupported output type: {output_type}')
        report = creator(config, report_type, user)
        self._create_query(report, config.get('filters'), user)
        return report

    def _create_table_report(self, config, report_type, user):
        table_fields = config.get('table_fields')
        if isinstance(table_fields, list):
            # Convert to expected format: [{"field": "field_id"}, ...]
            processed = []
            for field in table_fields:
                if isinstance(field, str):
                    processed.append({'field': field})
                elif isinstance(field, dict):
                    if 'field' not in field and 'field_id' in field:
                        field['field'] = field.pop('field_id')
                    processed.append(field)
            table_fields = processed

        report = TableReport(
            name=config.get('name', 'AI Generated Report'),
            report_type=report_type,
            table_fields=table_fields,
            order_by_field=config.get('order_by_field') or '',
            order_by_ascending=config.get('order_by_ascending', True),
            page_length=config.get('page_length', 100),
        )
        report._current_user = user
        report.save()
        return report

    def _create_bar_chart_report(self, config, report_type, user):
        fields = self._normalize_fields(config.get('fields'))
        report = BarChartReport(
            name=config.get('name', 'AI Generated Bar Chart'),
            report_type=report_type,
            axis_scale=config.get('axis_scale', 3),
            date_field=config.get('date_field', ''),
            axis_value_type=config.get('axis_value_type', 4),
            fields=fields,
            x_label=config.get('x_label') or '',
            y_label=config.get('y_label') or '',
            stacked=config.get('stacked', False),
            show_totals=config.get('show_totals', False),
        )
        report._current_user = user
        report.save()
        return report

    def _create_line_chart_report(self, config, report_type, user):
        fields = self._normalize_fields(config.get('fields'))
        report = LineChartReport(
            name=config.get('name', 'AI Generated Line Chart'),
            report_type=report_type,
            axis_scale=config.get('axis_scale', 3),
            date_field=config.get('date_field', ''),
            axis_value_type=config.get('axis_value_type', 4),
            fields=fields,
            x_label=config.get('x_label') or '',
            y_label=config.get('y_label') or '',
            show_totals=config.get('show_totals', False),
        )
        report._current_user = user
        report.save()
        return report

    def _create_pie_chart_report(self, config, report_type, user):
        fields = self._normalize_fields(config.get('fields'))
        report = PieChartReport(
            name=config.get('name', 'AI Generated Pie Chart'),
            report_type=report_type,
            axis_value_type=config.get('axis_value_type', 4),
            fields=fields,
            style=config.get('style', 1),
        )
        report._current_user = user
        report.save()
        return report

    def _create_single_value_report(self, config, report_type, user):
        report = SingleValueReport(
            name=config.get('name', 'AI Generated Single Value'),
            report_type=report_type,
            single_value_type=config.get('single_value_type', 1),
            field=config.get('field') or '',
            prefix=config.get('prefix') or '',
            decimal_places=config.get('decimal_places', 0),
        )
        report._current_user = user
        report.save()
        return report

    def _create_funnel_chart_report(self, config, report_type, user):
        fields = self._normalize_fields(config.get('fields'))
        report = FunnelChartReport(
            name=config.get('name', 'AI Generated Funnel Chart'),
            report_type=report_type,
            axis_value_type=config.get('axis_value_type', 4),
            fields=fields,
        )
        report._current_user = user
        report.save()
        return report

    @staticmethod
    def _normalize_fields(fields):
        if not fields:
            return None
        processed = []
        for field in fields:
            if isinstance(field, str):
                processed.append({'field': field})
            elif isinstance(field, dict):
                if 'field' not in field and 'field_id' in field:
                    field['field'] = field.pop('field_id')
                processed.append(field)
        return processed

    @staticmethod
    def _create_query(report, filters, user):
        rq = ReportQuery(
            report=report,
            name='Standard',
            query=filters if filters else None,
        )
        rq._current_user = user
        rq.save()
