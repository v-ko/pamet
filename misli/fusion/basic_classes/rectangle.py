from typing import Union, Tuple

from fusion.basic_classes import Point2D


class Rectangle:
    def __init__(self, x: float, y: float, w: float, h: float):
        self._x = x
        self._y = y
        self._w = w
        self._h = h

    @classmethod
    def from_points(
            cls, top_left: Point2D, bottom_right: Point2D) -> 'Rectangle':
        size = top_left - bottom_right
        x = min(top_left.x(), bottom_right.x())
        y = min(top_left.y(), bottom_right.y())
        w, h = abs(size.x()), abs(size.y())
        return cls(x, y, w, h)

    def __repr__(self):
        return ('<Rectangle x=%s y=%s width=%s height=%s ' % self.as_tuple())

    def __eq__(self, other: 'Rectangle'):
        return self.as_tuple() == other.as_tuple()

    def x(self) -> float:
        return self._x

    def y(self) -> float:
        return self._y

    def width(self) -> float:
        return self._w

    def height(self) -> float:
        return self._h

    def size(self) -> Point2D:
        return Point2D(self._w, self._h)

    def set_size(self, new_size: Point2D):
        self._w = new_size.x()
        self._h = new_size.y()

    def set_width(self, new_width: float):
        self._w = new_width

    def set_height(self, new_height: float):
        self._h = new_height

    def set_top_left(self, point: Point2D):
        self._x = point.x()
        self._y = point.y()

    def set_x(self, x: float):
        self._x = x

    def set_y(self, y: float):
        self._y = y

    def move_center(self, new_center: Point2D):
        self.set_top_left(new_center - self.size() / 2)

    def top(self) -> float:
        return self._y

    def left(self) -> float:
        return self._x

    def bottom(self) -> float:
        return self.y() + self.height()

    def right(self) -> float:
        return self.x() + self.width()

    def top_left(self) -> Point2D:
        return Point2D(self.x(), self.y())

    def top_right(self) -> Point2D:
        return Point2D(self.right(), self.top())

    def bottom_right(self) -> Point2D:
        return self.top_left() + Point2D(self.width(), self.height())

    def bottom_left(self) -> Point2D:
        return Point2D(self.left(), self.bottom())

    def center(self) -> Point2D:
        return self.top_left() + self.size() / 2

    def area(self) -> Point2D:
        return self.width() * self. height()

    def intersection(self, other: 'Rectangle') -> Union['Rectangle', None]:
        """Calculate the intersection of two rectangles

        Returns:
            Rectangle: The intersection between two rectangles. If the
                       intersection is not a rectangle - returns None.
        """
        a, b = self, other
        x1 = max(min(a.x(), a.right()), min(b.x(), b.right()))
        y1 = max(min(a.y(), a.bottom()), min(b.y(), b.bottom()))
        x2 = min(max(a.x(), a.right()), max(b.x(), b.right()))
        y2 = min(max(a.y(), a.bottom()), max(b.y(), b.bottom()))

        if not (x1 < x2 and y1 < y2):
            return None

        return type(self)(x1, y1, x2 - x1, y2 - y1)

    def intersects(self, other: 'Rectangle') -> bool:
        """Returns True if there's an intersection with the given rectangle
        otherwise returns False
        """
        if self.intersection(other):
            return True
        else:
            return False

    def contains(self, point: Point2D) -> bool:
        """Returns True if the rectangle contains the point, otherwise False
        """
        return ((self.x() < point.x() < self.right()) and
                (self.y() < point.y() < self.bottom()))

    def as_tuple(self) -> Tuple[float, float, float, float]:
        """Returns a list with the rectangle parameters ([x, y, w, h])
        """
        return (self._x, self._y, self._w, self._h)
