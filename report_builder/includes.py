# version = pip_version('django-advance-query-builder')
from ajax_helpers.html_include import SourceBase


class ChartJS(SourceBase):
    cdn_path = 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.5.1/chart.min.js'


class Dot(SourceBase):
    static_path = '/report_builder/dot/'
    js_filename = 'doT.js'


class JQueryExtendext(SourceBase):
    static_path = '/report_builder/jquery_extendext/'
    js_filename = 'jQuery.extendext.js'


class QueryBuilder(SourceBase):
    static_path = '/report_builder/query_builder/'
    css_filename = 'query-builder.default.css'
    js_filename = 'query-builder.min.js'


packages = {
    'query_builder': [JQueryExtendext, Dot, QueryBuilder],
}
