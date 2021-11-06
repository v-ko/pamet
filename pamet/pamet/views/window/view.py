import misli
from misli.gui import ViewState, wrap_and_register_view_state_type
from misli.gui import View, register_view_type


@wrap_and_register_view_state_type
class BrowserWindowViewState(ViewState):
    name: str = ''
    current_tab_id: str = ''


@register_view_type
class BrowserWindowView(View):
    def __init__(self, parent_id):
        View.__init__(
            self,
            parent_id=parent_id,
            initial_state=BrowserWindowViewState()
        )

    def current_tab(self):
        raise NotImplementedError
