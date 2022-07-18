from copy import copy
import math
from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QDesktopServices, QFontMetricsF, QPainter, QColor, QPainterPath, QPalette, QPolygon
from PySide6.QtCore import QPoint, QPointF, QRectF, QSize, QSizeF, QUrl, Qt, QRect
from misli.basic_classes.point2d import Point2D
from misli.basic_classes.rectangle import Rectangle
from misli.entity_library.change import Change
from misli.gui.utils.qt_widgets import bind_and_apply_state
from misli.gui.view_library.view_state import view_state_type
from misli.pubsub import Subscription

from pamet import channels, register_note_view_type
from pamet.actions import tab as tab_actions
from pamet.actions import note as note_actions
from pamet.constants import ALIGNMENT_GRID_UNIT, MAX_AUTOSIZE_HEIGHT, MAX_AUTOSIZE_WIDTH, MIN_NOTE_HEIGHT, MIN_NOTE_WIDTH, NOTE_MARGIN, PREFERRED_TEXT_NOTE_ASPECT_RATIO
from pamet.model.text_note import TextNote
from pamet.views.note.base_note_view import NoteView, NoteViewState
from pamet.desktop_app.helpers import elide_text, draw_text_lines

from misli import get_logger

log = get_logger(__name__)


@view_state_type
class TextNoteViewState(NoteViewState, TextNote):
    def text_rect(self,
                  note_width: float = None,
                  note_height: float = None) -> Rectangle:
        if note_width and note_height:
            size = Point2D(note_width, note_height)
        else:
            size = self.rect().size()
        size -= Point2D(2 * NOTE_MARGIN, 2 * NOTE_MARGIN)
        return Rectangle(NOTE_MARGIN, NOTE_MARGIN, *size.as_tuple())



@register_note_view_type(state_type=TextNoteViewState,
                         note_type=TextNote,
                         edit=False)
class TextNoteWidget(QLabel, NoteView):

    def __init__(self, parent, initial_state):
        QLabel.__init__(self, parent=parent)
        NoteView.__init__(self, initial_state=initial_state)
        self._page_subscription: Subscription = None

        font = self.font()
        font.setPointSizeF(14)
        self.setFont(font)

        self._elided_text_layout = None
        self._alignment = Qt.AlignHCenter
        self.setMargin(0)

        bind_and_apply_state(self, initial_state, self.on_state_change)
        # If there's a link - we watch for a page rename (and must unsubscribe
        # at destroyed)
        self.destroyed.connect(lambda: self.disconnect_from_page_changes())

    def left_mouse_double_click_event(self, position: Point2D):
        if not self.state().url:
            note_actions.start_editing_note(self.parent().parent_tab.state(),
                                            self.state().get_note())
        else:
            self.left_mouse_double_click_with_link(position)

    def left_mouse_double_click_with_link(self, position: Point2D):
        state = self.state()
        # If it's a custom schema - just ignore for now (start editing)
        if state.url.is_custom_uri():
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

            url_page = state.url.get_page()
            if url_page:
                self._elided_text_layout = elide_text(
                    url_page.name, state.text_rect(),
                    self.font())
            else:
                self._elided_text_layout = elide_text(state.text,
                                                      state.text_rect(),
                                                      self.font())

        if change.updated.url:
            url_page = state.url.get_page()
            if url_page and url_page.name:
                self.connect_to_page_changes(self.state().url.get_page())
            else:
                self.disconnect_from_page_changes()

    def paintEvent(self, event):
        state = self.state()

        painter = QPainter()
        painter.begin(self)

        draw_text_lines(painter, self._elided_text_layout.data,
                        self._alignment,
                        self.state().text_rect())

        # Draw the border
        pen = painter.pen()
        url = state.url

        if url.is_internal():
            if not url.get_page():
                pen.setStyle(Qt.DashLine)
                painter.setPen(pen)
            painter.drawRect(self.rect())
        elif url.is_external():
            p1 = self.rect().topRight()
            p2 = copy(p1)
            p1.setX(p1.x() - 10)
            p2.setY(p2.y() + 10)

            poly = QPolygon()
            poly << p1 << p2 << self.rect().topRight()

            path = QPainterPath()
            path.addPolygon(poly)
            brush = painter.brush()
            brush.setStyle(Qt.SolidPattern)
            brush.setColor(self.palette().color(QPalette.WindowText))
            painter.fillPath(path, brush)

            internal_border_rect = QRectF(self.rect())
            internal_border_rect.setSize(internal_border_rect.size() -
                                         QSizeF(1, 1))
            internal_border_rect.moveTopLeft(QPointF(0.5, 0.5))
            painter.drawRect(internal_border_rect)

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

    def connect_to_page_changes(self, page):
        if self._page_subscription:
            self.disconnect_from_page_changes()

        self._page_subscription = channels.entity_changes_by_id.subscribe(
            self.handle_page_change, index_val=page.id)

    def disconnect_from_page_changes(self):
        if self._page_subscription:
            self._page_subscription.unsubscribe()
            self._page_subscription = None

    def handle_page_change(self, change: Change):
        if change.is_delete() or change.updated.name:
            note_actions.apply_page_change_to_anchor_view(self.state())
