# version = pip_version('django-advanced-report-builder')
from ajax_helpers.html_include import SourceBase


class Dot(SourceBase):
    static_path = 'advanced_report_builder/dot/'
    js_filename = 'doT.js'


class JQueryExtendext(SourceBase):
    static_path = 'advanced_report_builder/jquery_extendext/'
    js_filename = 'jQuery.extendext.js'


class QueryBuilder(SourceBase):
    static_path = 'advanced_report_builder/query_builder/'
    css_filename = 'query-builder.default.css'
    js_filename = 'query-builder.min.js'


class DashboardInclude(SourceBase):
    static_path = 'advanced_report_builder/dashboard/'
    js_filename = 'dashboard.js'


class ChartJS(SourceBase):
    static_path = 'advanced_report_builder/chart-js/'
    js_filename = [
        'chart.min.js',
        'chartjs-adapter-moment.min.js',  # this does require moment however it's already included
        'chartjs-plugin-datalabels.min.js',
    ]


class D3(SourceBase):
    static_path = 'advanced_report_builder/d3/'
    js_filename = ['d3.min.js']


class D3Funnel(SourceBase):
    static_path = 'advanced_report_builder/d3-funnel/'
    js_filename = ['d3-funnel.min.js']


class FullCalendar(SourceBase):
    static_path = 'advanced_report_builder/fullcalendar/packages/'

    js_path = cdn_js_path = ''
    css_path = cdn_css_path = ''

    css_filename = ['core/main.css', 'daygrid/main.css', 'timegrid/main.css', 'list/main.css']

    js_filename = ['core/main.js', 'interaction/main.js', 'daygrid/main.js', 'timegrid/main.js', 'list/main.js']


class Moment(SourceBase):
    static_path = 'advanced_report_builder/moment/'
    js_path = cdn_js_path = ''
    js_filename = 'moment.min.js'


class FullCalendarYearView(SourceBase):
    static_path = 'advanced_report_builder/fullcalendar/packages/fullcalendar-yearview/'
    filename = 'main'


packages = {
    'query_builder': [JQueryExtendext, Dot, QueryBuilder],
    'full_calendar': [Moment, FullCalendar, FullCalendarYearView],
    'dashboard': [DashboardInclude],
    'funnel': [D3, D3Funnel],
}
