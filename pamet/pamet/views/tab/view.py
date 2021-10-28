from misli import gui
from misli.gui import View, ViewState, wrap_and_register_view_state_type


@wrap_and_register_view_state_type
class BrowserTabViewState(ViewState):
    name: str = ''
    page_view_id: str = None
    edit_view_id: str = None


class BrowserTabView(View):
    def __init__(self, parent_id):
        View.__init__(
            self,
            parent_id=parent_id,
            initial_state=BrowserTabViewState()
        )

    def page_view(self):
        return gui.view(self.state().page_view_id)
