from PySide2.QtCore import QRectF, QPointF, QLineF
from PySide2.QtGui import QFontMetrics

from misli.gui.desktop import defaultFont
from misli.gui.constants import INITIAL_EYE_Z


class Viewport(object):
    def __init__(self, _canvasWidget):
        self._canvasWidget = _canvasWidget

        self._font = defaultFont()
        self._font_metrics = QFontMetrics(self._font)

        self.center = QPointF()
        self.eyeHeight = INITIAL_EYE_Z  # self._font_metrics.lineSpacing()

    def __repr__(self):
        info = (self.center, self.eyeHeight)
        return '<Viewport center=%s eyeHeight=%s>' % info

    def heightScaleFactor(self):
        return self._font_metrics.lineSpacing() / self.eyeHeight

    def projectRect(self, rect):
        return QRectF(self.projectPoint(rect.topLeft()),
                      self.projectPoint(rect.bottomRight()))

    def projectLine(self, line):
        return QLineF(self.projectPoint(line.p1()),
                      self.projectPoint(line.p2()))

    def projectPoint(self, point):
        return QPointF(self.projectX(point.x()), self.projectY(point.y()))

    def projectX(self, xOnCanvas):
        xOnCanvas -= self.center.x()
        xOnCanvas *= self.heightScaleFactor()
        return xOnCanvas + self._canvasWidget.width() / 2

    def projectY(self, yOnCanvas):
        yOnCanvas -= self.center.y()
        yOnCanvas *= self.heightScaleFactor()
        return yOnCanvas + self._canvasWidget.height() / 2

    def unprojectPoint(self, point):
        return QPointF(self.unprojectX(point.x()), self.unprojectY(point.y()))

    def unprojectRect(self, rect):
        return QRectF(self.unprojectPoint(rect.topLeft()),
                      self.unprojectPoint(rect.bottomRight()))

    def unprojectX(self, xOnScreen):
        xOnScreen -= self._canvasWidget.width() / 2
        xOnScreen /= self.heightScaleFactor()
        return xOnScreen + self.center.x()

    def unprojectY(self, yOnScreen):
        yOnScreen -= self._canvasWidget.height() / 2
        yOnScreen /= self.heightScaleFactor()
        return yOnScreen + self.center.y()
