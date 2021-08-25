from typing import Tuple


class Color:
    def __init__(self, r: float, g: float, b: float, a: float):
        """Accepts normalized RGBA channel values (i.e. in the interval [0, 1])

        Args:
            r (float): Red channel value
            g (float): Green channel value
            b (float): Blue channel value
            a (float): Alpha channel value

        Raises:
            ValueError: When one of the values is outside of the [0, 1] range
        """
        if r > 1 or g > 1 or b > 1 or a > 1:
            raise ValueError

        self._r = r
        self._g = g
        self._b = b
        self._a = a

    def to_uint8_rgba_list(self) -> Tuple[float, float, float, float]:
        """Convert to a list of uint values (handy for initializing Qt QColor)

        Returns:
            [type]: A list of uint8 (in the interval [0, 255]) channel values
        """
        return tuple([c * 255 for c in self.as_tuple()])

    def as_tuple(self) -> Tuple[float, float, float, float]:
        """Returns a RGBA list (normalized values)"""
        return (self._r, self._g, self._b, self._a)
