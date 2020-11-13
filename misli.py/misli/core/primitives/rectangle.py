from PySide2.QtCore import QRectF
from .rectangle_base import RectangleBase


class Rectangle(QRectF, RectangleBase):
    def __init__(self, x, y, w, h):
        QRectF.__init__(self, x, y, w, h)

    @classmethod
    def from_QRectF(cls, qrectf):
        return cls(qrectf.left(), qrectf.top(),
                   qrectf.width(), qrectf.height())

    @classmethod
    def from_QRect(cls, qrect):
        return cls.from_QRectF(qrect)

    def to_QRectF(self):
        return QRectF(self.x(), self.y(), self.width(), self.height())
