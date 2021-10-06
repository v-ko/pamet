from typing import List, Union
from dataclasses import field
from datetime import datetime

from misli import get_logger
from misli import Entity, register_entity_type
from misli.helpers import datetime_from_string
from misli.basic_classes import Point2D, Rectangle, Color
from pamet.constants import DEFAULT_NOTE_HEIGHT, DEFAULT_NOTE_WIDTH
from pamet.constants import DEFAULT_BG_COLOR, DEFAULT_COLOR
from pamet.constants import MIN_NOTE_WIDTH, MIN_NOTE_HEIGHT
from pamet.constants import MAX_NOTE_WIDTH, MAX_NOTE_HEIGHT
from pamet.helpers import snap_to_grid
log = get_logger(__name__)


@register_entity_type
class Note(Entity):
    page_id: str = ''
    _x: float = 0
    _y: float = 0
    _width: float = DEFAULT_NOTE_WIDTH
    _height: float = DEFAULT_NOTE_HEIGHT
    color: tuple = field(
        default_factory=lambda: DEFAULT_COLOR)
    background_color: tuple = field(
        default_factory=lambda: DEFAULT_BG_COLOR)
    _content: dict = field(default_factory=dict)
    _time_created: datetime = field(
        default_factory=lambda: datetime.fromtimestamp(0))
    _time_modified: datetime = field(
        default_factory=lambda: datetime.fromtimestamp(0))
    tags: List[str] = field(default_factory=list)

    def __repr__(self):
        return '<Note id=%s>' % self.id

    def gid(self):
        return self.page_id, self.id

    def parent_gid(self):
        return self.page_id

    @property
    def content(self):
        return self._content

    @content.setter
    def content(self, new_content):
        if new_content == self._content:
            return

        self.time_modified = datetime.now()
        self._content = new_content

    def rect(self) -> Rectangle:
        return Rectangle(self.x, self.y, self.width, self.height)

    def set_color(self, color: Color):
        self.color = color.as_tuple()

    def get_color(self) -> Color:
        return Color(*self.color)

    def get_background_color(self) -> Color:
        return Color(*self.background_color)

    @property
    def width(self) -> float:
        return self._width

    @width.setter
    def width(self, width: float) -> float:
        width = min(MAX_NOTE_WIDTH, max(width, MIN_NOTE_WIDTH))
        self._width = snap_to_grid(width)

    @property
    def height(self) -> float:
        return self._height

    @height.setter
    def height(self, height: float):
        height = min(MAX_NOTE_HEIGHT, max(height, MIN_NOTE_HEIGHT))
        self._height = snap_to_grid(height)

    def size(self) -> Point2D:
        return Point2D(self.width, self.height)

    def set_size(self, new_size: Point2D):
        self.width = new_size.x()
        self.height = new_size.y()

    @property
    def x(self) -> float:
        return self._x

    @x.setter
    def x(self, x: float):
        self._x = snap_to_grid(x)

    @property
    def y(self) -> float:
        return self._y

    @y.setter
    def y(self, y: float) -> float:
        self._y = snap_to_grid(y)

    @property
    def time_created(self) -> datetime:
        return self._time_created

    @time_created.setter
    def time_created(self, new_dt: Union[datetime, str]):
        if isinstance(new_dt, datetime):
            self._time_created = new_dt.replace(microsecond=0)
        else:
            self._time_created = datetime_from_string(new_dt)

    @property
    def time_modified(self) -> datetime:
        return self._time_modified

    @time_modified.setter
    def time_modified(self, new_dt: Union[datetime, str]):
        if isinstance(new_dt, datetime):
            self._time_modified = new_dt.replace(microsecond=0)
        else:
            self._time_modified = datetime_from_string(new_dt)
