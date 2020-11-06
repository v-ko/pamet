from .text_note_widget import TextNoteWidget
from PySide2.QtGui import QPainter
from PySide2.QtCore import QPointF, QRectF, QSizeF


class RedirectNoteWidget(TextNoteWidget):
    def __init__(self, note, parent=None):
        super().__init__(note, parent=parent)

    def paintEvent(self, event):
        super().paintEvent(event)

        painter = QPainter()
        painter.begin(self)

        pen = painter.pen()
        pen.setCosmetic(True)
        painter.setPen(pen)

        size = self.size()
        border_rect = QRectF(0, 0, size.width(), size.height())
        painter.drawRect(border_rect)

        painter.end()
