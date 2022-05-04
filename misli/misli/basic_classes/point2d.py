from typing import Tuple
import math


class Point2D:
    def __init__(self, x: float = 0, y: float = 0):
        self._x = x
        self._y = y

    def __repr__(self):
        return '<Point x=%s y=%s>' % (self.x(), self.y())

    def __add__(self, other: 'Point2D') -> 'Point2D':
        return Point2D(self.x() + other.x(), self.y() + other.y())

    def __sub__(self, other: 'Point2D') -> 'Point2D':
        return Point2D(self.x() - other.x(), self.y() - other.y())

    def __truediv__(self, k) -> 'Point2D':
        return Point2D(self.x() / k, self.y() / k)

    def __round__(self):
        return Point2D(round(self.x()), round(self.y()))

    def __mul__(self, k):
        return Point2D(self.x() * k, self.y() * k)

    def __rmul__(self, k):
        return self.__mul__(k)

    def x(self) -> float:
        return self._x

    def y(self) -> float:
        return self._y

    def as_tuple(self) -> Tuple[float, float]:
        return (self._x, self._y)

    def distance_to(self, point: 'Point2D') -> float:
        distance = math.sqrt(
            (self.x() - point.x())**2 + (self.y() - point.y())**2)
        return distance
