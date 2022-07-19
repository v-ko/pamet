from dataclasses import field
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from misli.basic_classes.point2d import Point2D
from misli.basic_classes.rectangle import Rectangle
from misli.gui.view_library.view import View
from misli.gui import ViewState, view_state_type

import pamet
from pamet.model import Note
from pamet.model.arrow import ArrowAnchorType
from pamet.actions import tab as tab_actions
from pamet.actions import note as note_actions

@view_state_type
class NoteViewState(ViewState, Note):
    note_gid: str = ''
    badges: list = field(default_factory=list, init=False, repr=False)

    def __post_init__(self):
        if not self.note_gid:
            raise Exception('All note views should have a mapped note.')

    def update_from_note(self, note: Note):
        self.replace(**note.asdict())

    def get_note(self):
        return pamet.find_one(gid=self.note_gid)


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

    def arrow_anchor(self, anchor_type: ArrowAnchorType) -> Point2D:
        """Returns the center position for a specific arrow anchor.

        Raises: Does not support the ArrowAnchorType.AUTO
        """
        rect: Rectangle = self.state().rect()

        match anchor_type:
            case ArrowAnchorType.MID_LEFT:
                return rect.top_left() + Point2D(0, rect.height() / 2)
            case ArrowAnchorType.TOP_MID:
                return rect.top_left() + Point2D(rect.width() / 2, 0)
            case ArrowAnchorType.MID_RIGHT:
                return rect.top_right() + Point2D(0, rect.height() / 2)
            case ArrowAnchorType.BOTTOM_MID:
                return rect.bottom_left() + Point2D(rect.width() / 2)
            case _:
                raise Exception
