from email.errors import InvalidMultipartContentTransferEncodingDefect
from fusion.gui.utils.qt_widgets import bind_and_apply_state
from fusion.gui.view_library.view import View


class QtView(View):
    def __init__(self, initial_state, on_state_change=None) -> None:
        View.__init__(self, initial_state=initial_state)

        if not on_state_change:
            on_state_change = getattr(self, 'on_state_change')
            if not on_state_change:
                return

        bind_and_apply_state(self, initial_state, on_state_change)
