import math
from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QFontMetricsF, QPainter, QColor
from PySide6.QtCore import QPointF, QRectF, QSizeF, Qt, QRect
from misli.basic_classes.point2d import Point2D
from misli.basic_classes.rectangle import Rectangle
from misli.gui.utils.qt_widgets import bind_and_apply_state
from misli.gui.view_library.view_state import view_state_type

from pamet import register_note_view_type
from pamet.actions import note as note_actions
from pamet.constants import ALIGNMENT_GRID_UNIT, MAX_AUTOSIZE_HEIGHT, MAX_AUTOSIZE_WIDTH, MIN_NOTE_HEIGHT, MIN_NOTE_WIDTH, NOTE_MARGIN, PREFERRED_TEXT_NOTE_ASPECT_RATIO
from pamet.model.note import Note
from pamet.model.text_note import TextNote
from pamet.views.note.base_note_view import NoteView, NoteViewState
from pamet.desktop_app.helpers import elide_text, draw_text_lines

from misli import get_logger

log = get_logger(__name__)


@view_state_type
class TextNoteViewState(NoteViewState, TextNote):
    pass


@register_note_view_type(state_type=TextNoteViewState,
                         note_type=TextNote,
                         edit=False)
class TextNoteWidget(QLabel, NoteView):

    def __init__(self, parent, initial_state):
        QLabel.__init__(self, parent=parent)
        NoteView.__init__(self, initial_state=initial_state)

        font = self.font()
        font.setPointSizeF(14)
        self.setFont(font)

        self._elided_text_layout = None
        self._alignment = Qt.AlignHCenter
        self.setMargin(0)

        bind_and_apply_state(self, initial_state, self.on_state_change)

    def left_mouse_double_click_event(self, position: Point2D):
        note_actions.start_editing_note(self.parent().parent_tab.state(),
                                        self.state().get_note())

    def on_state_change(self, change):
        state = change.last_state()
        if change.updated.color or change.updated.background_color:
            palette = self.palette()

            fg_col = QColor(*state.get_color().to_uint8_rgba_list())
            bg_col = QColor(*state.get_background_color().to_uint8_rgba_list())

            palette.setColor(self.backgroundRole(), bg_col)
            palette.setColor(self.foregroundRole(), fg_col)

            self.setPalette(palette)

        if change.updated.geometry:
            self.setGeometry(QRect(*state.geometry))

        if change.updated.text or change.updated.geometry:
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

            if '\n' in state.text:
                self._alignment = Qt.AlignLeft
            else:
                self._alignment = Qt.AlignHCenter

            self._elided_text_layout = elide_text(state.text,
                                                  state.text_rect(), font)

            # self.setText('<p style="line-height:%s%%;margin-top:-5px;margin-right
            # :5px;margin-bottom:5px">%s</p>' %
            #      (100*20/float(font_metrics.lineSpacing()), _elided_text_layout))
            # self.setText(elided_text)

    def paintEvent(self, event):
        if not self._elided_text_layout:
            return

        painter = QPainter()
        painter.begin(self)

        draw_text_lines(painter, self._elided_text_layout.data,
                        self._alignment,
                        self.state().text_rect())
        painter.end()

    def minimal_nonelided_size(self) -> Point2D:
        """Do a binary search to get the minimal note size"""
        state = self.state()
        text = state.text

        if not text:
            return Point2D(MIN_NOTE_WIDTH, MIN_NOTE_HEIGHT)

        # Start with the largest possible rect
        test_note = TextNote(page_id='__DUMMY__')
        max_w = MAX_AUTOSIZE_WIDTH

        unit = ALIGNMENT_GRID_UNIT
        min_width_u = int(MIN_NOTE_WIDTH / unit)
        min_height_u = int(MIN_NOTE_HEIGHT / unit)

        # Do a binary search for the proper width (keeping the aspect ratio)
        low_width_bound = 0
        high_width_bound = round(max_w / unit - min_height_u)
        while (high_width_bound - low_width_bound) > 0:
            test_width_it = (high_width_bound + low_width_bound) // 2
            test_width_u = min_width_u + test_width_it
            test_height_u = round(test_width_u /
                                  PREFERRED_TEXT_NOTE_ASPECT_RATIO)

            test_note.set_rect(
                Rectangle(0, 0, test_width_u * unit, test_height_u * unit))

            if elide_text(text, test_note.text_rect(), self.font()).is_elided:
                low_width_bound = test_width_it + 1
            else:
                high_width_bound = test_width_it

        # Fine adjust the size by reducing it one unit per step and
        # stopping upon text elide
        width_u = min_width_u + low_width_bound
        height_u = round(width_u / PREFERRED_TEXT_NOTE_ASPECT_RATIO)
        width = width_u * unit
        height = height_u * unit

        # Adjust the height
        rect = test_note.rect()
        rect.set_size(width, height)
        while True:
            rect.set_height(rect.height() - unit)
            test_note.set_rect(rect)

            if elide_text(text, test_note.text_rect(), self.font()).is_elided:
                break
            else:
                height = rect.height()

        # Adjust the width. We check for changes in the text, because
        # even elided text (if it's multi line) can have empty space laterally
        text_layout = elide_text(text, test_note.text_rect(), self.font())
        text_before_adjust = text_layout.text()
        while True:
            rect.set_width(rect.width() - unit)
            test_note.set_rect(rect)
            text_layout = elide_text(text, test_note.text_rect(), self.font())
            text = text_layout.text()
            if text != text_before_adjust:
                break
            else:
                width = rect.width()

        return Point2D(width, height)
