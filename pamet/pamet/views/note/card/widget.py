
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QPaintEvent, QPainter, QResizeEvent
from PySide6.QtWidgets import QWidget

from misli.entity_library.change import Change
from misli.gui.utils.qt_widgets import bind_and_apply_state
from misli.gui.view_library.view_state import view_state_type
from pamet.desktop_app import default_note_font
from pamet.desktop_app.helpers import draw_text_lines, elide_text
from pamet.helpers import Url
from pamet.model.card_note import CardNote
from pamet.note_view_lib import register_note_view_type
from pamet.views.note.anchor.view_mixin import LinkNoteViewMixin
from pamet.views.note.base_note_view import NoteView, NoteViewState
from pamet.views.note.image.image_label import ImageLabel
from pamet.views.note.qt_helpers import draw_link_decorations

from .ui_widget import Ui_CardNoteWidget


@view_state_type
class CardNoteViewState(NoteViewState, CardNote):
    pass


@register_note_view_type(state_type=CardNoteViewState,
                         note_type=CardNote,
                         edit=False)
class CardNoteWidget(QWidget, NoteView, LinkNoteViewMixin):

    def __init__(self, parent, initial_state):
        QWidget.__init__(self, parent)
        NoteView.__init__(self, initial_state=initial_state)
        LinkNoteViewMixin.__init__(self)

        self.ui = Ui_CardNoteWidget()
        self.ui.setupUi(self)

        self.setFont(default_note_font())
        self.image_label = ImageLabel(self)

        bind_and_apply_state(self, initial_state, self.on_state_change)

    def on_state_change(self, change: Change):
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

        if change.updated.local_image_url:
            local_url: Url = state.local_image_url
            self.image_label.update_image_cache(local_url)

        if change.updated.text or \
                change.updated.geometry \
                or change.updated.url:
            if '\n' in state.text:
                self._alignment = Qt.AlignLeft
            else:
                self._alignment = Qt.AlignHCenter

            url_page = state.url.get_page()
            if url_page:
                self._elided_text_layout = elide_text(url_page.name,
                                                      state.text_rect(),
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

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter()
        painter.begin(self)

        draw_text_lines(painter, self._elided_text_layout.data,
                        self._alignment, self.state().text_rect())
        draw_link_decorations(self, painter)
        # Debug drawing
        # image_rect, text_rect = self.image_and_text_rects()
        # painter.setPen(Qt.red)
        # painter.drawRect(*image_rect.as_tuple())
        # painter.drawRect(*text_rect.as_tuple())
        painter.end()

    def resizeEvent(self, event: QResizeEvent):
        image_label_rect = QRect(*self.state().image_rect().as_tuple())
        self.image_label.setGeometry(image_label_rect)
