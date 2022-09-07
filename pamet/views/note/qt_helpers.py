from copy import copy
from typing import Union
from PySide6.QtCore import QPointF, QRectF, QSizeF, Qt
from PySide6.QtGui import QPainter, QPainterPath, QPalette, QPolygon
from fusion.util.point2d import Point2D
from fusion.util.rectangle import Rectangle

import pamet
from pamet.constants import ALIGNMENT_GRID_UNIT, DEFAULT_NOTE_HEIGHT, DEFAULT_NOTE_WIDTH, MAX_AUTOSIZE_WIDTH, MAX_NOTE_WIDTH
from pamet.constants import MIN_NOTE_HEIGHT, MIN_NOTE_WIDTH
from pamet.constants import PREFERRED_TEXT_NOTE_ASPECT_RATIO
from pamet.desktop_app import default_note_font
from pamet.desktop_app.util import TextLayout, elide_text
from pamet.util.url import Url
from pamet.model.card_note import CardNote
from pamet.model.image_note import ImageNote
from pamet.model.text_note import TextNote


def minimal_nonelided_size(note: Union[TextNote, CardNote]) -> Point2D:
    """Do a binary search to get the minimal note size"""
    default_note_size = Point2D(DEFAULT_NOTE_WIDTH, DEFAULT_NOTE_HEIGHT)
    note_font = default_note_font()

    # If it's an image note - fit to the image (if no image - default size)
    if type(note) == ImageNote:  # Card inherits Image!, don't use isinstance
        if note.image_size:
            return note.image_rect()
        else:
            return default_note_size

    text = note.text
    if not text:
        return default_note_size

    # Start with the largest possible rect
    # test_note = state.get_note()
    max_w = MAX_NOTE_WIDTH

    unit = ALIGNMENT_GRID_UNIT
    min_width_u = int(MIN_NOTE_WIDTH / unit)
    min_height_u = int(MIN_NOTE_HEIGHT / unit)

    # Do a binary search for the proper width (keeping the aspect ratio)
    low_width_bound = 0
    high_width_bound = round(max_w / unit - min_width_u)
    while (high_width_bound - low_width_bound) > 0:
        test_width_it = (high_width_bound + low_width_bound) // 2
        test_width_u = min_width_u + test_width_it
        test_height_u = round(test_width_u / PREFERRED_TEXT_NOTE_ASPECT_RATIO)

        # test_note.set_rect(
        #     Rectangle(0, 0, test_width_u * unit, test_height_u * unit))
        test_size = Point2D(test_width_u * unit, test_height_u * unit)
        text_layout = elide_text(text, note.text_rect(test_size), note_font)
        if text_layout.is_elided:
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
    rect = Rectangle(0, 0, width, height)
    text_layout = TextLayout()
    while rect.width() >= MIN_NOTE_WIDTH and rect.height() >= MIN_NOTE_HEIGHT:
        if text_layout.is_elided:
            break
        else:
            height = rect.height()

        rect.set_height(rect.height() - unit)
        text_layout = elide_text(text, note.text_rect(rect.size()), note_font)

    # Adjust the width. We check for changes in the text, because
    # even elided text (if it's multi line) can have empty space laterally
    text_layout = elide_text(text, note.text_rect(Point2D(width, height)),
                             note_font)
    text_before_adjust = text_layout.text()
    text = text_before_adjust
    rect = Rectangle(0, 0, width, height)
    while rect.width() >= MIN_NOTE_WIDTH and rect.height() >= MIN_NOTE_HEIGHT:
        if text != text_before_adjust:
            break
        else:
            width = rect.width()

        rect.set_width(rect.width() - unit)
        # test_note.set_rect(rect)
        text_layout = elide_text(text, note.text_rect(rect.size()), note_font)
        text = text_layout.text()

    return Point2D(width, height)


def draw_link_decorations(note_widget, painter: QPainter):
    state = note_widget.state()

    # Draw the link decorations
    pen = painter.pen()
    url: Url = state.url

    internal_border_rect = QRectF(note_widget.rect())
    internal_border_rect.setSize(internal_border_rect.size() - QSizeF(1, 1))
    internal_border_rect.moveTopLeft(QPointF(0.5, 0.5))

    if url.is_internal():
        # For internal notes draw only a solid border
        # But if the target page is missing - draw it with a dashed pattern
        if not pamet.page(url.get_page_id()):
            pen.setStyle(Qt.DashLine)
            painter.setPen(pen)
        painter.drawRect(internal_border_rect)

    elif url.is_external():
        # Draw the external link decoration
        # Draw a triangular marker in the upper left corner
        p1 = note_widget.rect().topRight()
        p2 = copy(p1)
        p1.setX(p1.x() - 10)
        p2.setY(p2.y() + 10)

        poly = QPolygon()
        poly << p1 << p2 << note_widget.rect().topRight()

        path = QPainterPath()
        path.addPolygon(poly)
        brush = painter.brush()
        brush.setStyle(Qt.SolidPattern)
        brush.setColor(note_widget.palette().color(QPalette.WindowText))
        painter.fillPath(path, brush)

        # Draw the solid border
        painter.drawRect(internal_border_rect)