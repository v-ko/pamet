class Color:
    def __init__(self, r, g, b, a):
        if r > 1 or g > 1 or b > 1 or a > 1:
            raise ValueError

        self._r = r
        self._g = g
        self._b = b
        self._a = a

    def to_uint8_rgba_list(self):
        return [c * 255 for c in [self._r, self._g, self._b, self._a]]
