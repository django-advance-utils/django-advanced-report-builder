from django_modals.widgets.widgets import Toggle


class RBToggle(Toggle):
    def __init__(self, attrs=None, check_test=None):
        if attrs is None:
            attrs = {'data-onstyle': 'success', 'data-on': 'YES', 'data-off': 'NO'}

        super().__init__(attrs, check_test)
