from PySide2.QtGui import QColor

from .color_base import ColorBase


class Color(ColorBase):
    def __init__(self, r, g, b, a):
        self.r = r
        self.g = g
        self.b = b
        self.a = a

    def state(self):
        return [self.r, self.g, self.b, self.a]

    def to_QColor(self):
        return QColor(*[c * 255 for c in self.state()])
