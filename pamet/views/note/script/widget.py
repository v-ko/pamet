from copy import copy
from PySide6.QtCore import QPoint, QPointF, QRectF, QSizeF, Qt
from PySide6.QtGui import QPainter, QPainterPath, QPalette, QPolygon
from fusion.util.point2d import Point2D

from fusion.libs.state import view_state_type
from pamet import desktop_app
from pamet.desktop_app.util import draw_text_lines
from pamet.model.script_note import ScriptNote
from pamet.note_view_lib import register_note_view_type
from pamet.views.note.base.state import NoteViewState
from pamet.views.note.text.widget import TextNoteWidget


@view_state_type
class ScriptNoteViewState(NoteViewState, ScriptNote):
    pass


@register_note_view_type(state_type=ScriptNoteViewState,
                         note_type=ScriptNote,
                         edit=False)
class ScriptNoteWidget(TextNoteWidget):

    def __init__(self, parent, initial_state):
        TextNoteWidget.__init__(self, parent, initial_state)

    def left_mouse_double_click_event(self, position: Point2D):
        desktop_app.script_runner.run(self.state().get_note())

    def paintEvent(self, event):
        painter = QPainter()
        painter.begin(self)

        draw_text_lines(painter, self._elided_text_layout.data,
                        self._alignment,
                        self.state().text_rect())

        # Draw the link decorations
        pen = painter.pen()

        internal_border_rect = QRectF(self.rect())
        internal_border_rect.setSize(internal_border_rect.size() -
                                     QSizeF(1, 1))
        internal_border_rect.moveTopLeft(QPointF(0.5, 0.5))

        # Draw the external link decoration
        # Draw a triangular marker in the upper left corner
        top_right = self.rect().topRight()
        p1 = copy(top_right)
        p1.setX(p1.x() - 10)
        p2 = copy(p1)
        p2.setY(p1.y() + 10)
        p3 = copy(p1)
        p3.setX(top_right.x())
        p3.setY(p1.y() + 5)

        offset = QPoint(-3, 3)
        p1 += offset
        p2 += offset
        p3 += offset

        poly = QPolygon()
        poly << p1 << p2 << p3

        path = QPainterPath()
        path.addPolygon(poly)
        brush = painter.brush()
        brush.setStyle(Qt.SolidPattern)
        brush.setColor(self.palette().color(QPalette.WindowText))
        painter.fillPath(path, brush)

        # Draw the solid border
        painter.drawRect(internal_border_rect)

        painter.end()
