import math


class Point2D:
    def __init__(self, x: float, y: float):
        self._x = x
        self._y = y

    @classmethod
    def from_coords(cls, coords: list):
        if len(coords) != 2:
            raise ValueError

        x = coords[0]
        y = coords[1]

        return cls(x, y)

    def __repr__(self):
        return '<Point x=%s y=%s>' % (self.x(), self.y())

    def __add__(self, other: 'Point2D'):
        return Point2D(self.x() + other.x(), self.y() + other.y())

    def __sub__(self, other: 'Point2D'):
        return Point2D(self.x() - other.x(), self.y() - other.y())

    def __truediv__(self, k):
        return Point2D(self.x() / k, self.y() / k)

    def x(self):
        return self._x

    def y(self):
        return self._y

    def to_list(self):
        return [self._x, self._y]

    def distance_to(self, point: 'Point2D'):
        distance = math.sqrt(
            (self.x() - point.x())**2 + (self.y() - point.y())**2)
        return distance
