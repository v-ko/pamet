from misli import gui
from misli.gui import View, ViewState, wrap_and_register_view_state_type

SIDEBAR_WIDTH = 100
MIN_TAB_WIDTH = SIDEBAR_WIDTH * 1.1


@wrap_and_register_view_state_type
class TabViewState(ViewState):
    name: str = ''
    page_view_id: str = None
    edit_view_id: str = None
    right_sidebar_view_id: str = None
    right_sidebar_visible: bool = False
    page_properties_open: bool = False


class TabView(View):
    def __init__(self, parent_id):
        View.__init__(
            self,
            parent_id=parent_id,
            initial_state=TabViewState()
        )

    def page_view(self):
        return gui.view(self.state().page_view_id)
