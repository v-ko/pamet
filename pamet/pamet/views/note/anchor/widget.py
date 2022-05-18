from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QPainter, QColor
from PySide6.QtCore import Qt, QRect

from misli.gui import ViewState, view_state_type
from pamet import register_note_view_type
from pamet.model.anchor_note import AnchorNote
from pamet.views.note.base_note_view import NoteView
from pamet.desktop_app.helpers import elide_text, draw_text_lines


from misli import get_logger
log = get_logger(__name__)


@view_state_type
class AnchorViewState(ViewState, AnchorNote):
    pass


@register_note_view_type(state_type=AnchorViewState,
                         note_type=AnchorNote,
                         edit=False)
class AnchorViewWidget(QLabel, NoteView):
    def __init__(self, parent):
        NoteView.__init__(
            self, parent=parent, initial_state=AnchorViewState())
        QLabel.__init__(self, '')

        self._elided_text_layout = []
        self._alignment = Qt.AlignHCenter
        self.setMargin(0)

    def on_state_update(self):
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
