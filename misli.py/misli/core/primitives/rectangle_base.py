class RectangleBase():
    def __init__(self, x, y, w, h):
        self._x = x
        self._y = y
        self._w = w
        self._h = h

    @classmethod
    def from_points(cls, top_left, bottom_right):
        size = top_left - bottom_right
        w, h = abs(size.x()), abs(size.y())
        return cls(top_left.x(), top_left.y(), w, h)

    def intersects(self, rectangle):
        raise NotImplementedError
