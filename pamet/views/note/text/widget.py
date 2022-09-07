from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QPainter, QColor
from PySide6.QtCore import Qt, QRect

from fusion.platform.qt_widgets import bind_and_apply_state
from fusion.libs.state import view_state_type

import pamet
from pamet import register_note_view_type
from pamet.desktop_app import default_note_font
from pamet.model.text_note import TextNote
from pamet.views.note.anchor.view_mixin import LinkNoteViewMixin
from pamet.views.note.base.view import NoteView
from pamet.views.note.base.state import NoteViewState
from pamet.desktop_app.util import elide_text, draw_text_lines

from fusion import get_logger
from pamet.views.note.qt_helpers import draw_link_decorations

log = get_logger(__name__)


@view_state_type
class TextNoteViewState(NoteViewState, TextNote):
    pass


@register_note_view_type(state_type=TextNoteViewState,
                         note_type=TextNote,
                         edit=False)
class TextNoteWidget(QLabel, NoteView, LinkNoteViewMixin):

    def __init__(self, parent, initial_state):
        QLabel.__init__(self, parent=parent)
        NoteView.__init__(self, parent=parent, initial_state=initial_state)
        LinkNoteViewMixin.__init__(self)

        self.setFont(default_note_font())

        self._elided_text_layout = None
        self._alignment = Qt.AlignHCenter
        self.setMargin(0)

        bind_and_apply_state(self, initial_state, self.on_state_change)
        # If there's a link - we watch for a page rename (and must unsubscribe
        # at destroyed)
        self.destroyed.connect(lambda: self.disconnect_from_page_changes())

    @property
    def displayed_text(self):
        if not self._elided_text_layout:
            return '!! Text not processed !!'
        return self._elided_text_layout.text()

    def on_state_change(self, change):
        state = change.last_state()
        if change.updated.color or change.updated.background_color:

            fg_col = QColor(*state.get_color().to_uint8_rgba_list())
            bg_col = QColor(*state.get_background_color().to_uint8_rgba_list())

            palette = self.palette()
            palette.setColor(self.backgroundRole(), bg_col)
            palette.setColor(self.foregroundRole(), fg_col)
            self.setPalette(palette)

        if change.updated.geometry:
            self.setGeometry(QRect(*state.geometry))

        if change.updated.text or \
                change.updated.geometry \
                or change.updated.url:
            # font = self.font()
            # font.setPixelSize(20)
            # font.setPointSizeF(note_props['font_size'] * font.pointSizeF())
            # font.setPointSizeF(14)
            # self.setFont(font)

            # font_metrics = QFontMetrics(self.font())
            # print('Font ascent', font_metrics.ascent())
            # print('Font descent', font_metrics.descent())
            # print('Font height', font_metrics.height())
            # print('Font leading', font_metrics.leading())
            # print('Font lineSpacing', font_metrics.lineSpacing())
            # print('Font pointSizeF', self.font().pointSizeF())

            # self.setText('<p style="line-height:%s%%;margin-top:-5px;margin-right
            # :5px;margin-bottom:5px">%s</p>' %
            #      (100*20/float(font_metrics.lineSpacing()), _elided_text_layout))
            # self.setText(elided_text)

            if '\n' in state.text:
                self._alignment = Qt.AlignLeft
            else:
                self._alignment = Qt.AlignHCenter

            self.recalculate_elided_text()

        if change.updated.url:
            url_page = pamet.page(state.url.get_page_id())
            if url_page and url_page.name:
                self.connect_to_page_changes(url_page.id)
            else:
                self.disconnect_from_page_changes()

    def paintEvent(self, event):
        painter = QPainter()
        painter.begin(self)

        draw_text_lines(painter, self._elided_text_layout.data,
                        self._alignment,
                        self.state().text_rect())
        draw_link_decorations(self, painter)
        painter.end()
