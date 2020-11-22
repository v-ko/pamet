from PySide2.QtCore import QPointF
from .point_base import PointBase


class Point(PointBase, QPointF):
    def __init__(self, x, y):
        QPointF.__init__(self, x, y)

    @classmethod
    def from_QPointF(cls, qpointf):
        return cls(qpointf.x(), qpointf.y())

    def to_QPointF(self):
        return QPointF(self.x(), self.y())
