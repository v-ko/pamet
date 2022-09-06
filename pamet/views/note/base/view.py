from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from fusion.util.point2d import Point2D
from fusion.view import View

import pamet
from pamet.actions import window as window_actions
from pamet.actions import tab as tab_actions
from pamet.actions import note as note_actions


class NoteView(View):
    recieves_double_click_events: bool = False

    def __init__(self, parent, initial_state):
        View.__init__(self, initial_state=initial_state)
        self.parent_page = parent

    def left_mouse_double_click_event(self, position: Point2D):
        url = self.state().url
        if url.is_empty() or url.is_custom():
            note_actions.start_editing_note(
                self.parent_page.parent_tab.state(),
                self.state().get_note())
        else:
            self.left_mouse_double_click_with_link(position)

    def left_mouse_double_click_with_link(self, position: Point2D):
        state = self.state()

        # If there's a linked page - go to it
        if state.url.is_internal():
            page = pamet.page(state.url.get_page_id())
            if page:
                tab_actions.go_to_url(self.parent_page.parent_tab.state(),
                                      page.url())
            else:
                super().left_mouse_double_click_event(position)
        # IMPLEMENT opening no schema urls (non-page names) and http/https
        else:
            QDesktopServices.openUrl(QUrl(str(state.url)))

    def middle_click_event(self, position: Point2D):
        url = self.state().url
        page = pamet.page(url.get_page_id())

        if not page:
            return

        window_view = self.parent_page.parent_tab.parent_window
        window_actions.new_browser_tab(window_view.state(), page)
