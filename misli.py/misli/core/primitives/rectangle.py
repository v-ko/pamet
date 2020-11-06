from PySide2.QtCore import QRectF
from .rectangle_base import RectangleBase


class Rectangle(RectangleBase):
    def __init__(self, x, y, w, h):
        self.qrectf = QRectF(x, y, w, h)

    def intersects(self, rectangle):
        return self.qrectf.intersects(rectangle.qrectf)
