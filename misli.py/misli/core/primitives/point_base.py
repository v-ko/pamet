class PointBase:
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

    def intersects(self, rectangle):
        raise NotImplementedError

    def to_coords(self):
        return [self._x, self._y]
