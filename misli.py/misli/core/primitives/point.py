import math


class Point:
    def __init__(self, x, y):
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

    def __add__(self, other):
        return Point(self.x() + other.x(), self.y() + other.y())

    def __sub__(self, other):
        return Point(self.x() - other.x(), self.y() - other.y())

    def __truediv__(self, k):
        return Point(self.x() / k, self.y() / k)

    def x(self):
        return self._x

    def y(self):
        return self._y

    def intersects(self, rectangle):
        raise NotImplementedError

    def to_list(self):
        return [self._x, self._y]

    def distance_to(self, point):
        distance = math.sqrt(
            (self.x() - point.x())**2 + (self.y() - point.y())**2)
        return distance
