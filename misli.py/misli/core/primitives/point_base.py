class PointBase():
    def __init__(self, x, y):
        self._x = x
        self._y = y

    def intersects(self, rectangle):
        raise NotImplementedError
