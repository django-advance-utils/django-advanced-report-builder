from importlib import import_module, metadata
from inspect import isclass, stack, getmodule
from django.templatetags.static import static
from django.utils.safestring import mark_safe


class SourceBase:

    static_path = None
    cdn_path = None
    filename = None
    js_filename = None
    css_filename = None
    legacy_js = None
    js_path = cdn_js_path = 'js/'
    css_path = cdn_css_path = 'css/'
    cdn_scheme = 'https://'

    def __init__(self, version, legacy=False):
        self.root = None
        self._cdn = None
        self.version = version
        self._version = None
        self.legacy = legacy

    @property
    def version_qs(self):
        return self._version

    @property
    def cdn(self):
        return self._cdn

    @cdn.setter
    def cdn(self, cdn):
        if cdn != self._cdn:
            self.root = (self.cdn_scheme + self.cdn_path) if cdn else static(self.static_path)
            self._version = '?v=' + self.version if not cdn and self.version else ''
            self._cdn = cdn

    def combine_filename(self, path, filename):
        if not isinstance(filename, (tuple, list)):
            filename = [filename]
        return [path + f + self.version_qs for f in filename]

    def _js_filename(self):
        if self.legacy and self.legacy_js:
            filename = self.legacy_js
        elif self.js_filename:
            filename = self.js_filename
        elif isinstance(self.filename, (tuple, list)):
            filename = [f + '.js' for f in self.filename]
        elif self.filename:
            filename = self.filename + '.js'
        else:
            return []
        return self.combine_filename(self.cdn_js_path if self.cdn else self.js_path, filename)

    def _css_filename(self):
        if self.css_filename:
            filename = self.css_filename
        elif isinstance(self.filename, (tuple, list)):
            filename = [f + '.css' for f in self.filename]
        elif self.filename:
            filename = self.filename + '.css'
        else:
            return []
        return self.combine_filename(self.cdn_css_path if self.cdn else self.css_path, filename)

    def javascript(self):
        return ''.join([f'<script src="{self.root + f}"></script>' for f in self._js_filename()])

    def css(self):
        return ''.join([f'<link href="{self.root + f}" rel="stylesheet">' for f in self._css_filename()])

    def includes(self, cdn=False):
        cdn = cdn or False
        if self.static_path is None:
            self.cdn = True
        elif self.cdn_path is None:
            self.cdn = False
        else:
            self.cdn = cdn
        return self.javascript() + self.css()


def html_include(library=None, cdn=False, module=None, legacy=False):
    """
    Returns a string with javascript and css includes defined in a subclass of SourceBase in the calling module or
    defined in passed module as a module or string.
    """
    if isinstance(module, str):
        module = import_module(module)
    elif not module:
        module = getmodule(stack()[1][0])
    if not library:
        library = 'DefaultInclude'
    version = getattr(module, 'version', '')
    packages = getattr(module, 'packages', None)
    if packages and library in packages:
        return mark_safe('\n'.join([lib(version, legacy).includes(cdn) for lib in packages[library]]))
    source_class = getattr(module, library, None)
    if isclass(source_class) and issubclass(source_class, SourceBase):
        return mark_safe(source_class(version, legacy).includes(cdn))
    return ''


def pip_version(package):
    try:
        return metadata.version(package)
    except metadata.PackageNotFoundError:
        return 'local'
