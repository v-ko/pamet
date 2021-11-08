from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QPainter, QColor
from PySide6.QtCore import Qt, QRect

from misli.gui.view_library import register_view_type
from pamet.views.note.base_note_view import NoteView, NoteViewState
from pamet.desktop_app.helpers import elide_text, draw_text_lines


from misli import get_logger
log = get_logger(__name__)


@register_view_type(priority=1, entity_type='TextNote', edit=False)
class TextNoteWidget(QLabel, NoteView):
    def __init__(self, parent_id):
        NoteView.__init__(
            self, parent_id=parent_id, initial_state=NoteViewState())
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
        # font.setPixelSize(20)
        # font.setPointSizeF(note_props['font_size'] * font.pointSizeF())
        font.setPointSizeF(14)
        self.setFont(font)

        # font_metrics = QFontMetrics(self.font())
        # print('Font ascent', font_metrics.ascent())
        # print('Font descent', font_metrics.descent())
        # print('Font height', font_metrics.height())
        # print('Font leading', font_metrics.leading())
        # print('Font lineSpacing', font_metrics.lineSpacing())
        # print('Font pointSizeF', self.font().pointSizeF())

        if '\n' in note.text:
            self._alignment = Qt.AlignLeft
        else:
            self._alignment = Qt.AlignHCenter

        self._elided_text_layout = elide_text(note.text, self.rect(), font)

        # self.setText('<p style="line-height:%s%%;margin-top:-5px;margin-right
        # :5px;margin-bottom:5px">%s</p>' %
        #      (100*20/float(font_metrics.lineSpacing()), _elided_text_layout))
        # self.setText(elided_text)

    def paintEvent(self, event):
        if not self._elided_text_layout:
            return

        painter = QPainter()
        painter.begin(self)

        draw_text_lines(
            painter, self._elided_text_layout, self._alignment, self.rect())
        painter.end()
