from copy import copy
from PySide6.QtGui import QDesktopServices, QPainter, QColor, QPainterPath, QPalette, QPolygon
from PySide6.QtCore import QPoint, QSize, QUrl, Qt, QRect
from misli.basic_classes.point2d import Point2D
from misli.entity_library.change import Change
from misli.gui.view_library.view_state import view_state_type
from misli.pubsub import Subscription

from pamet import channels, register_note_view_type
from pamet.actions import tab as tab_actions
from pamet.actions import note as note_actions
from pamet.model.anchor_note import AnchorNote
from pamet.views.note.base_note_view import NoteViewState
from pamet.desktop_app.helpers import elide_text, draw_text_lines

from misli import get_logger
from pamet.views.note.text.widget import TextNoteWidget

log = get_logger(__name__)


@view_state_type
class AnchorViewState(NoteViewState, AnchorNote):
    initial_validity_check_done: bool = False
    cached_link_page_name: str = ''

    def __post_init__(self):
        super().__post_init__()

        # Avoid doing link validity checks when copying the state (but do them
        # on the initial state creation. A bit hacky)
        if not self.initial_validity_check_done:
            self.update_link_validity()
            self.initial_validity_check_done = True

    def update_from_note(self, note: AnchorNote):
        old_url = self.url
        super().update_from_note(note)

        if note.url != old_url:
            self.update_link_validity()

    @property
    def url(self):
        return AnchorNote.url.fget(self)

    @url.setter
    def url(self, new_url):
        self.update_link_validity()
        AnchorNote.url.fset(self, new_url)

    def update_link_validity(self):
        linked_page = self.linked_page()
        if linked_page:
            self.cached_link_page_name = linked_page.name
        else:
            self.cached_link_page_name = None

    @property
    def valid_internal_link(self):
        return bool(self.cached_link_page_name)


@register_note_view_type(state_type=AnchorViewState,
                         note_type=AnchorNote,
                         edit=False)
class AnchorWidget(TextNoteWidget):

    def __init__(self, parent, initial_state):
        self._page_subscription: Subscription = None

        TextNoteWidget.__init__(self, parent, initial_state)
        self.destroyed.connect(lambda: self.disconnect_from_page_changes())

    def left_mouse_double_click_event(self, position: Point2D):
        state = self.state()
        # If it's a custom schema - just ignore for now (start editing)
        if state.is_custom_uri():
            super().left_mouse_double_click_event(position)

        # If there's a linked page - go to it
        elif state.is_internal_link():
            if state.valid_internal_link:
                tab_actions.tab_go_to_page(self.parent().tab_widget.state(),
                                           state.linked_page())
            else:
                super().left_mouse_double_click_event(position)
        # IMPLEMENT opening no schema urls (non-page names) and http/https
        else:
            QDesktopServices.openUrl(QUrl(state.url))

    def on_state_change(self, change):
        state = change.last_state()
        if change.updated.color or change.updated.background_color:
            palette = self.palette()

            fg_col = QColor(*state.get_color().to_uint8_rgba_list())
            bg_col = QColor(*state.get_background_color().to_uint8_rgba_list())

            palette.setColor(QPalette.Window, bg_col)
            palette.setColor(QPalette.WindowText, fg_col)

            self.setPalette(palette)

        if change.updated.geometry:
            self.setGeometry(QRect(*state.geometry))

        if change.updated.text or \
                change.updated.geometry or \
                change.updated.cached_link_page_name:
            if '\n' in state.text:
                self._alignment = Qt.AlignLeft
            else:
                self._alignment = Qt.AlignHCenter

            if state.valid_internal_link:
                self._elided_text_layout = elide_text(
                    state.cached_link_page_name, self.text_rect(), self.font())
            else:
                self._elided_text_layout = elide_text(state.text,
                                                      self.text_rect(),
                                                      self.font())

        if change.updated.cached_link_page_name:
            if state.cached_link_page_name:
                self.connect_to_page_changes(self.state().linked_page())
            else:
                self.disconnect_from_page_changes()

        # if change.updated.cached_link_page_name:
        #     style_sheet = '''
        #     QLabel{
        #         border: 1px solid blue;
        #     }
        #     '''
        #     self.setStyleSheet(style_sheet)
        #         # self.styleSheet().append('border-style: 1px solid black;'))

    def paintEvent(self, event):
        painter = QPainter()
        painter.begin(self)

        draw_text_lines(painter, self._elided_text_layout.data,
                        self._alignment, self.rect())

        state: AnchorViewState = self.state()

        # Draw the border
        pen = painter.pen()
        if state.is_internal_link():
            if not state.valid_internal_link:
                pen.setStyle(Qt.DashLine)
                painter.setPen(pen)
            painter.drawRect(self.rect())
        elif state.is_external_link():
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

            internal_border_rect = self.rect()
            internal_border_rect.setSize(internal_border_rect.size() -
                                         QSize(1, 1))
            internal_border_rect.moveTopLeft(QPoint(0.5, 0.5))
            painter.drawRect(internal_border_rect)

        painter.end()

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
