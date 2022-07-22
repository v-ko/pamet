from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from misli.basic_classes.point2d import Point2D
from misli.gui.view_library.view import View

from pamet.actions import tab as tab_actions
from pamet.actions import note as note_actions


class NoteView(View):
    recieves_double_click_events: bool = False

    def __init__(self, initial_state):
        View.__init__(
            self,
            initial_state=initial_state
        )

    def left_mouse_double_click_event(self, position: Point2D):
        if not self.state().url:
            note_actions.start_editing_note(self.parent().parent_tab.state(),
                                            self.state().get_note())
        else:
            self.left_mouse_double_click_with_link(position)

    def left_mouse_double_click_with_link(self, position: Point2D):
        state = self.state()
        # If it's a custom schema - just ignore for now (start editing)
        if state.url.is_custom():
            super().left_mouse_double_click_event(position)

        # If there's a linked page - go to it
        elif state.url.is_internal():
            page = state.url.get_page()
            if page:
                tab_actions.go_to_url(self.parent().tab_widget.state(),
                                      page.url())
            else:
                super().left_mouse_double_click_event(position)
        # IMPLEMENT opening no schema urls (non-page names) and http/https
        else:
            QDesktopServices.openUrl(QUrl(str(state.url)))
