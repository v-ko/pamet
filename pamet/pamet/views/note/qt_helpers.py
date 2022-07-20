from copy import copy
from PySide6.QtCore import QPointF, QRectF, QSizeF, Qt
from PySide6.QtGui import QPainter, QPainterPath, QPalette, QPolygon
from misli.basic_classes.point2d import Point2D
from misli.basic_classes.rectangle import Rectangle
from pamet.constants import ALIGNMENT_GRID_UNIT, MAX_AUTOSIZE_WIDTH
from pamet.constants import MIN_NOTE_HEIGHT, MIN_NOTE_WIDTH
from pamet.constants import PREFERRED_TEXT_NOTE_ASPECT_RATIO
from pamet.desktop_app.helpers import TextLayout, elide_text
from pamet.helpers import Url


def minimal_nonelided_size(note_widget) -> Point2D:
    """Do a binary search to get the minimal note size"""
    state = note_widget.state()
    text = state.text

    if not text:
        return Point2D(MIN_NOTE_WIDTH, MIN_NOTE_HEIGHT)

    # Start with the largest possible rect
    # test_note = state.get_note()
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
        test_height_u = round(test_width_u / PREFERRED_TEXT_NOTE_ASPECT_RATIO)

        # test_note.set_rect(
        #     Rectangle(0, 0, test_width_u * unit, test_height_u * unit))
        test_size = Point2D(test_width_u * unit, test_height_u * unit)
        if elide_text(text, note_widget.text_rect(test_size),
                      note_widget.font()).is_elided:
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
    # rect.set_size(Point2D(width, height))
    text_layout = TextLayout()
    while rect.width() >= MIN_NOTE_WIDTH and rect.height() >= MIN_NOTE_HEIGHT:
        if text_layout.is_elided:
            break
        else:
            height = rect.height()

        rect.set_height(rect.height() - unit)
        # test_note.set_rect(rect)
        text_layout = elide_text(text, note_widget.text_rect(rect.size()),
                                 note_widget.font())

    # Adjust the width. We check for changes in the text, because
    # even elided text (if it's multi line) can have empty space laterally
    text_layout = elide_text(text, note_widget.text_rect(rect.size()),
                             note_widget.font())
    text_before_adjust = text_layout.text()
    text = text_before_adjust
    while rect.width() >= MIN_NOTE_WIDTH and rect.height() >= MIN_NOTE_HEIGHT:
        if text != text_before_adjust:
            break
        else:
            width = rect.width()

        rect.set_width(rect.width() - unit)
        # test_note.set_rect(rect)
        text_layout = elide_text(text, note_widget.text_rect(rect.size()),
                                 note_widget.font())
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
        if not url.get_page():
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