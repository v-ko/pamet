from copy import copy
from typing import Tuple
from html2text import element_style
from misli.basic_classes.point2d import Point2D
from misli.basic_classes.rectangle import Rectangle

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QPaintEvent, QPainter, QResizeEvent
from PySide6.QtWidgets import QWidget

from misli.entity_library.change import Change
from misli.gui.utils.qt_widgets import bind_and_apply_state
from misli.gui.view_library.view_state import view_state_type
from pamet.constants import NOTE_MARGIN
from pamet.desktop_app.helpers import draw_text_lines, elide_text
from pamet.helpers import Url
from pamet.model.card_note import CardNote
from pamet.note_view_lib import register_note_view_type
from pamet.views.note.anchor.view_mixin import LinkNoteViewMixin
from pamet.views.note.base_note_view import NoteView, NoteViewState
from pamet.views.note.image.image_label import ImageLabel
from pamet.views.note.qt_helpers import draw_link_decorations

from .ui_widget import Ui_CardNoteWidget

MIN_AR_DELTA_FOR_HORIZONTAL_ALIGN = 0.5
IMAGE_PORTION_FOR_HORIZONTAL_ALIGN = 0.8


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

        font = self.font()
        font.setPointSizeF(14)
        self.setFont(font)

        self.image_label = ImageLabel(self)

        bind_and_apply_state(self, initial_state, self.on_state_change)

    def image_and_text_rects(self,
                             for_size: Point2D = None
                             ) -> Tuple[Rectangle, Rectangle]:
        """Returns the rectangles where the image and text should fit.
        They are relative to the note view"""
        image_rect = Rectangle(0, 0, 0, 0)
        text_rect = Rectangle(0, 0, 0, 0)

        # Fit the image in the note
        # If there's no image - assume rectangular
        image_aspect_ratio = 1
        image = self.image_label.image()
        if image:
            image_aspect_ratio = image.width() / image.height()
        else:
            raise Exception
        if for_size:
            note_size = for_size
        else:
            note_size = self.state().size()
        note_aspect_ratio = note_size.x() / note_size.y()
        ar_delta = note_aspect_ratio - image_aspect_ratio
        if ar_delta > MIN_AR_DELTA_FOR_HORIZONTAL_ALIGN:
            # Calc image size from AR
            image_rect.set_size(
                Point2D(note_size.y() * image_aspect_ratio, note_size.y()))
            # Prep the field (will apply margins below)
            text_field = Rectangle(*image_rect.top_right().as_tuple(),
                                   note_size.x() - image_rect.width(),
                                   note_size.y())

        else:
            # Decide on a good image to text ratio. E.g. 5:1 vertically
            # Image rect
            image_field = Rectangle(
                0, 0, note_size.x(),
                note_size.y() * IMAGE_PORTION_FOR_HORIZONTAL_ALIGN)
            image_field_AR = image_field.width() / image_field.height()
            if image_field_AR > image_aspect_ratio:
                # The avalable space is wider than the image
                image_rect.set_size(
                    Point2D(image_field.height() * image_aspect_ratio,
                            image_field.height()))
            else:
                # The available space is higher (when we fit the image width)
                image_rect.set_size(
                    Point2D(image_field.width(),
                            image_field.width() / image_aspect_ratio))
                image_field = copy(image_rect)

            image_rect.move_center(image_field.center())

            # Text rect
            text_field = Rectangle(image_field.bottom_left().x(),
                                   image_field.bottom_left().y(),
                                   note_size.x(),
                                   note_size.y() - image_field.height())

        # Apply margins to get the text field
        text_rect = text_field
        text_rect.set_top_left(text_rect.top_left() +
                               Point2D(NOTE_MARGIN, NOTE_MARGIN))
        text_rect.set_size(text_rect.size() -
                           Point2D(2 * NOTE_MARGIN, 2 * NOTE_MARGIN))

        return image_rect, text_rect

    def image_rect(self, for_size: Point2D = None):
        return self.image_and_text_rects(for_size)[0]

    def text_rect(self, for_size: Point2D = None):
        return self.image_and_text_rects(for_size)[1]

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
                                                      self.text_rect(),
                                                      self.font())
            else:
                self._elided_text_layout = elide_text(state.text,
                                                      self.text_rect(),
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
                        self._alignment, self.text_rect())
        draw_link_decorations(self, painter)
        # Debug drawing
        # image_rect, text_rect = self.image_and_text_rects()
        # painter.setPen(Qt.red)
        # painter.drawRect(*image_rect.as_tuple())
        # painter.drawRect(*text_rect.as_tuple())
        painter.end()

    def resizeEvent(self, event: QResizeEvent):
        image_label_rect = QRect(*self.image_rect().as_tuple())
        self.image_label.setGeometry(image_label_rect)
