from PySide2.QtGui import QColor

from .color_base import ColorBase


class Color(ColorBase):
    def __init__(self, r, g, b, a):
        super().__init__(r, g, b, a)

    def state(self):
        return [self._r, self._g, self._b, self._a]

    def to_QColor(self):
        return QColor(*[c * 255 for c in self.state()])
