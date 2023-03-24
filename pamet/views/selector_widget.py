from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QColor, QImage, QPainter, QBrush
from PySide6.QtGui import QCursor
from PySide6.QtCore import Qt, QRect, QPoint, QTimer, Signal
from PySide6.QtWidgets import QApplication


class SelectorWidget(QWidget):
    # Signals
    image_selected = Signal(QImage)

    def __init__(self):

        super(SelectorWidget, self).__init__()

        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.dragging = False
        self.taking_screenshot = False
        self.mousePressPoint = QPoint()
        self.selectedRect = QRect()

    def finish(self):
        self.taking_screenshot = False
        self.close()

    def keyPressEvent(self, event):
        self.finish()

    def rectFromAnyTwoPoints(self, p1, p2):
        x1 = min(p1.x(), p2.x())
        y1 = min(p1.y(), p2.y())
        w = max(p1.x(), p2.x()) - x1
        h = max(p1.y(), p2.y()) - y1

        return QRect(x1, y1, w, h)

    def grabSelectedRect(self):
        screen = self.window().windowHandle().screen()
        pixmap = screen.grabWindow(0)

        if not self.selectedRect.isValid():
            print('Selected rect is not valid')
            self.finish()
            return

        region = pixmap.copy(self.selectedRect)

        # This has to be before setting the clipboard contents
        # because otherwise the notfy-send hangs
        # subprocess.run(['notify-send', 'Copied snippet to clipboard'])

        clipboard = QApplication.clipboard()
        clipboard.setImage(region.toImage())

        self.finish()

    def mousePressEvent(self, event):
        self.mousePressPoint = event.pos()
        self.dragging = True

    def mouseReleaseEvent(self, event):
        self.selectedRect = self.rectFromAnyTwoPoints(
            self.mousePressPoint, event.pos())

        self.taking_screenshot = True
        self.dragging = False
        self.update()
        QTimer.singleShot(100, self.grabSelectedRect)  # Wait for the DM update

    def mouseMoveEvent(self, event):
        self.update()

    def paintEvent(self, event):
        painter = QPainter()

        painter.begin(self)

        if self.taking_screenshot:
            painter.setBrush(QBrush(QColor(250, 250, 250, 0), Qt.SolidPattern))
            painter.setPen(Qt.NoPen)
            painter.drawRect(self.rect())

            return

        painter.setBrush(QBrush(QColor(100, 100, 100, 40), Qt.CrossPattern))
        painter.setPen(Qt.NoPen)

        painter.drawRect(self.rect())

        painter.setPen(Qt.red)
        painter.setBrush(QBrush(QColor(100, 100, 100, 0), Qt.SolidPattern))

        if self.dragging:
            p1 = self.mousePressPoint
            p2 = self.mapFromGlobal(QCursor.pos())

            painter.drawRect(self.rectFromAnyTwoPoints(p1, p2))

        painter.end()
