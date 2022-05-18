from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QPainter, QColor
from PySide6.QtCore import Qt, QRect
from misli.gui.utils.qt_widgets.qtview import QtView
from misli.gui.view_library.view_state import view_state_type

from pamet import register_note_view_type
from pamet.model.text_note import TextNote
from pamet.views.note.base_note_view import NoteViewState
from pamet.desktop_app.helpers import elide_text, draw_text_lines

from misli import get_logger

log = get_logger(__name__)


@view_state_type
class TextNoteViewState(NoteViewState, TextNote):
    pass


@register_note_view_type(state_type=TextNoteViewState,
                         note_type=TextNote,
                         edit=False)
class TextNoteWidget(QLabel, QtView):

    def __init__(self, parent, initial_state):
        QLabel.__init__(self, parent=parent)
        QtView.__init__(self,
                        initial_state=initial_state,
                        on_state_change=self.on_state_change)

        self._elided_text_layout = []
        self._alignment = Qt.AlignHCenter
        self.setMargin(0)

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

        geometry_updated = change.updated.geometry
        if geometry_updated:
            # self.setGeometry(QRect(*note.rect().as_tuple()))
            self.setGeometry(QRect(*nv_state.geometry))

        if change.updated.text or geometry_updated:
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

            if '\n' in nv_state.text:
                self._alignment = Qt.AlignLeft
            else:
                self._alignment = Qt.AlignHCenter

            self._elided_text_layout = elide_text(nv_state.text, self.rect(),
                                                  font)

            # self.setText('<p style="line-height:%s%%;margin-top:-5px;margin-right
            # :5px;margin-bottom:5px">%s</p>' %
            #      (100*20/float(font_metrics.lineSpacing()), _elided_text_layout))
            # self.setText(elided_text)

        self.parent().on_child_updated(self)  # TODO: optimize

    def paintEvent(self, event):
        if not self._elided_text_layout:
            return

        painter = QPainter()
        painter.begin(self)

        draw_text_lines(painter, self._elided_text_layout, self._alignment,
                        self.rect())
        painter.end()
