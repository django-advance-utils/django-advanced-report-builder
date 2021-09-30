from .html_include import SourceBase, pip_version

version = pip_version('django-advance-query-builder')


class ChartJS(SourceBase):
    cdn_path = 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.5.1/chart.min.js'


packages = {
    'report_builder': [ChartJS],
}
