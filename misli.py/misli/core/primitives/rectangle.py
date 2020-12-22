from . import Point


class Rectangle:
    def __init__(self, x, y, w, h):
        self._x = x
        self._y = y
        self._w = w
        self._h = h

    @classmethod
    def from_points(cls, top_left, bottom_right):
        size = top_left - bottom_right
        x = min(top_left.x(), bottom_right.x())
        y = min(top_left.y(), bottom_right.y())
        w, h = abs(size.x()), abs(size.y())
        return cls(x, y, w, h)

    def __repr__(self):
        return ('<Rectangle x=%s y=%s width=%s height=%s ' %
                tuple(self.to_list()))

    def __eq__(self, other):
        return self.to_list() == other.to_list()

    def x(self):
        return self._x

    def y(self):
        return self._y

    def width(self):
        return self._w

    def height(self):
        return self._h

    def top(self):
        return self._y

    def left(self):
        return self._x

    def bottom(self):
        return self.y() + self.height()

    def right(self):
        return self.x() + self.width()

    def top_left(self):
        return Point(self.x(), self.y())

    def top_right(self):
        return Point(self.right(), self.top())

    def bottom_right(self):
        return self.top_left() + Point(self.width(), self.height())

    def bottom_left(self):
        return Point(self.left(), self.bottom())

    def intersection(self, other):
        a, b = self, other
        x1 = max(min(a.x(), a.right()), min(b.x(), b.right()))
        y1 = max(min(a.y(), a.bottom()), min(b.y(), b.bottom()))
        x2 = min(max(a.x(), a.right()), max(b.x(), b.right()))
        y2 = min(max(a.y(), a.bottom()), max(b.y(), b.bottom()))

        if x1 < x2 and y1 < y2:
            return type(self)(x1, y1, x2 - x1, y2 - y1)

    def intersects(self, other):
        if self.intersection(other):
            return True
        else:
            return False

    def contains(self, point):
        return ((self.x() < point.x() < self.right()) and
                (self.y() < point.y() < self.bottom()))

    def to_list(self):
        return [self._x, self._y, self._w, self._h]
