class RectangleBase():
    def __init__(self, x, y, w, h):
        self._x = x
        self._y = y
        self._w = w
        self._h = h

    def intersects(self, rectangle):
        raise NotImplementedError
