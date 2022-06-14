from dataclasses import field
from typing import ClassVar
from urllib.parse import ParseResult, urlparse

from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QDesktopServices, QPainter, QColor
from PySide6.QtCore import QUrl, Qt, QRect
from misli.basic_classes.point2d import Point2D
from misli.gui.utils.qt_widgets import bind_and_apply_state
from misli.gui.view_library.view import View
from misli.gui.view_library.view_state import view_state_type

from pamet import register_note_view_type
from pamet.actions import tab as tab_actions
from pamet.model.anchor_note import AnchorNote
from pamet.views.note.base_note_view import NoteViewState
from pamet.desktop_app.helpers import elide_text, draw_text_lines

from misli import get_logger
from pamet.views.note.text.widget import TextNoteWidget

log = get_logger(__name__)


@view_state_type
class AnchorViewState(NoteViewState, AnchorNote):
    pass


@register_note_view_type(state_type=AnchorViewState,
                         note_type=AnchorNote,
                         edit=False)
class AnchorWidget(TextNoteWidget):
    def left_mouse_double_click_event(self, position: Point2D):
        # If it's a custom schema - just ignore for now (start editing)
        if self.state().is_custom_uri():
            super().left_mouse_double_click_event(position)

        # If there's a linked page - go to it
        elif self.state().linked_page():
            tab_actions.tab_go_to_page(self.parent().tab_widget.state(),
                                       self.state().linked_page())

        # IMPLEMENT opening no schema urls (non-page names) and http/https
        else:
            QDesktopServices.openUrl(QUrl(self.state().url))

    def on_state_change(self, change):
        nv_state = change.last_state()
        if change.updated.color or change.updated.background_color:
            palette = self.palette()

            fg_col = QColor(*nv_state.get_color().to_uint8_rgba_list())
            bg_col = QColor(
                *nv_state.get_background_color().to_uint8_rgba_list())

            palette.setColor(self.backgroundRole(), bg_col)
            palette.setColor(self.foregroundRole(), fg_col)

            self.setPalette(palette)

        if change.updated.geometry:
            self.setGeometry(QRect(*nv_state.geometry))

        if change.updated.text or change.updated.geometry:
            font = self.font()
            font.setPointSizeF(14)
            self.setFont(font)

            if '\n' in nv_state.text:
                self._alignment = Qt.AlignLeft
            else:
                self._alignment = Qt.AlignHCenter

            self._elided_text_layout = elide_text(nv_state.text, self.rect(),
                                                  font)

    def paintEvent(self, event):
        if not self._elided_text_layout:
            return

        painter = QPainter()
        painter.begin(self)

        draw_text_lines(painter, self._elided_text_layout, self._alignment,
                        self.rect())
        painter.drawRect(self.rect())
        painter.end()
