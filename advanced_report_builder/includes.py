from ajax_helpers.html_include import SourceBase, pip_version

# Stamped as ?v= on every file below. Static is served with a far-future expiry, so without it a
# browser that has ever loaded dashboard.js or the query builder keeps that copy until a hard refresh.
version = pip_version('django-advanced-report-builder')


class Dot(SourceBase):
    static_path = 'advanced_report_builder/dot/'
    js_filename = 'doT.js'


class JQueryExtendext(SourceBase):
    static_path = 'advanced_report_builder/jquery_extendext/'
    js_filename = 'jQuery.extendext.js'


class QueryBuilder(SourceBase):
    static_path = 'advanced_report_builder/query_builder/'
    css_filename = 'query-builder.default.css'
    # known-rules.js: load a saved query without losing it to one rule the builder cannot show.
    js_filename = ['query-builder.min.js', 'known-rules.js']


class DashboardInclude(SourceBase):
    static_path = 'advanced_report_builder/dashboard/'
    js_filename = 'dashboard.js'


class RecordNavInclude(SourceBase):
    static_path = 'advanced_report_builder/record_nav/'
    js_filename = 'record_nav.js'


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
    'record_nav': [RecordNavInclude],
}
