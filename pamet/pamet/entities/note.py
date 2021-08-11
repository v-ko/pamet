from dataclasses import dataclass, field

from misli import get_logger
from misli import Entity, register_entity
from misli.basic_classes import Point2D, Rectangle, Color
from pamet.constants import DEFAULT_NOTE_HEIGHT, DEFAULT_NOTE_WIDTH
from pamet.constants import DEFAULT_BG_COLOR, DEFAULT_COLOR
from pamet.constants import MIN_NOTE_WIDTH, MIN_NOTE_HEIGHT
from pamet.constants import MAX_NOTE_WIDTH, MAX_NOTE_HEIGHT
from pamet.helpers import snap_to_grid
log = get_logger(__name__)


@register_entity
@dataclass
class Note(Entity):
    page_id: str = ''
    _x: float = 0
    _y: float = 0
    _width: float = DEFAULT_NOTE_WIDTH
    _height: float = DEFAULT_NOTE_HEIGHT
    color: list = field(
        default_factory=lambda: DEFAULT_COLOR.copy())
    background_color: list = field(
        default_factory=lambda: DEFAULT_BG_COLOR.copy())
    text: str = ''

    def __repr__(self):
        return '<Note id=%s>' % self.id

    def gid(self):
        return self.page_id, self.id

    def rect(self):
        return Rectangle(self.x, self.y, self.width, self.height)

    def set_color(self, color: Color):
        self.color = color.to_list()

    def get_color(self):
        return Color(*self.color)

    def get_background_color(self):
        return Color(*self.background_color)

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, width: float):
        width = min(MAX_NOTE_WIDTH, max(width, MIN_NOTE_WIDTH))
        self._width = snap_to_grid(width)

    @property
    def height(self):
        return self._height

    @height.setter
    def height(self, height: float):
        height = min(MAX_NOTE_HEIGHT, max(height, MIN_NOTE_HEIGHT))
        self._height = snap_to_grid(height)

    def size(self):
        return Point2D(self.width, self.height)

    def set_size(self, new_size: Point2D):
        self.width = new_size.x()
        self.height = new_size.y()

    @property
    def x(self):
        return self._x

    @x.setter
    def x(self, x: float):
        self._x = snap_to_grid(x)

    @property
    def y(self):
        return self._y

    @y.setter
    def y(self, y: float):
        self._y = snap_to_grid(y)
