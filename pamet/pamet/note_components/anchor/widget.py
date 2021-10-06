from dataclasses import dataclass

from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QPainter, QColor
from PySide6.QtCore import Qt, QRect

from misli.gui import ViewState, register_view_state_type
from misli.gui.view_library import register_view_type
from pamet.note_components.base_note_view import NoteView
from pamet.model import Note
from pamet.desktop.helpers import elide_text, draw_text_lines


from misli import get_logger
log = get_logger(__name__)


@register_view_state_type
class NoteViewState(ViewState):
    note: Note = None


@register_view_type(entity_type='AnchorNote', edit=False)
class AnchorViewWidget(QLabel, NoteView):
    def __init__(self, parent_id):
        NoteView.__init__(
            self, parent_id=parent_id, initial_state=NoteViewState())
        QLabel.__init__(self, '')

        self._elided_text_layout = []
        self._alignment = Qt.AlignHCenter
        self.setMargin(0)

    def handle_state_update(self):
        note = self.note
        palette = self.palette()

        fg_col = QColor(*note.get_color().to_uint8_rgba_list())
        bg_col = QColor(*note.get_background_color().to_uint8_rgba_list())

        palette.setColor(self.backgroundRole(), bg_col)
        palette.setColor(self.foregroundRole(), fg_col)

        self.setPalette(palette)
        self.setGeometry(QRect(*note.rect().as_tuple()))

        font = self.font()
        font.setPointSizeF(14)
        self.setFont(font)

        if '\n' in note.text:
            self._alignment = Qt.AlignLeft
        else:
            self._alignment = Qt.AlignHCenter

        self._elided_text_layout = elide_text(note.text, self.rect(), font)

    def paintEvent(self, event):
        if not self._elided_text_layout:
            return

        painter = QPainter()
        painter.begin(self)

        draw_text_lines(
            painter, self._elided_text_layout, self._alignment, self.rect())
        pen = painter.pen()
        pen.setCosmetic(True)
        painter.setPen(pen)

        painter.drawRect(self.rect())
        painter.end()
