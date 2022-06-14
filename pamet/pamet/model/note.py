from __future__ import annotations

from typing import List, Union
from dataclasses import field
from datetime import datetime

from misli import get_logger
from misli import Entity, entity_type
from misli.helpers import datetime_from_string
from misli.basic_classes import Point2D, Rectangle, Color
from pamet.constants import DEFAULT_NOTE_HEIGHT, DEFAULT_NOTE_WIDTH
from pamet.constants import DEFAULT_BG_COLOR, DEFAULT_COLOR
from pamet.constants import MIN_NOTE_WIDTH, MIN_NOTE_HEIGHT
from pamet.constants import MAX_NOTE_WIDTH, MAX_NOTE_HEIGHT
from pamet.helpers import snap_to_grid

log = get_logger(__name__)


@entity_type
class Note(Entity):
    page_id: str = ''
    geometry: list = field(default_factory=lambda:
                           [0, 0, DEFAULT_NOTE_WIDTH, DEFAULT_NOTE_HEIGHT])
    color: tuple = field(default_factory=lambda: DEFAULT_COLOR)
    background_color: tuple = field(default_factory=lambda: DEFAULT_BG_COLOR)
    content: dict = field(default_factory=dict)
    created: datetime = field(
        default_factory=lambda: datetime.fromtimestamp(0))
    modified: datetime = field(
        default_factory=lambda: datetime.fromtimestamp(0))
    tags: List[str] = field(default_factory=list)
    type_name: str = ''

    def __repr__(self):
        return '<Note id=%s>' % self.id

    def __post_init__(self):
        self.type_name = type(self).__name__
        if not self.page_id:
            raise Exception

    def asdict(self):
        self_dict = super().asdict()
        self_dict['type_name'] = type(self).__name__
        return self_dict

    def gid(self):
        return self.page_id, self.id

    def parent_gid(self):
        return self.page_id

    def rect(self) -> Rectangle:
        return Rectangle(*self.geometry)

    def set_color(self, color: Color):
        self.color = color.as_tuple()

    def get_color(self) -> Color:
        return Color(*self.color)

    def get_background_color(self) -> Color:
        return Color(*self.background_color)

    @property
    def width(self) -> float:
        return self.geometry[2]

    @width.setter
    def width(self, width: float) -> float:
        width = min(MAX_NOTE_WIDTH, max(width, MIN_NOTE_WIDTH))
        self.geometry[2] = snap_to_grid(width)

    @property
    def height(self) -> float:
        return self.geometry[3]

    @height.setter
    def height(self, height: float):
        height = min(MAX_NOTE_HEIGHT, max(height, MIN_NOTE_HEIGHT))
        self.geometry[3] = snap_to_grid(height)

    @property
    def x(self) -> float:
        return self.geometry[0]

    @x.setter
    def x(self, x: float):
        self.geometry[0] = snap_to_grid(x)

    @property
    def y(self) -> float:
        return self.geometry[1]

    @y.setter
    def y(self, y: float) -> float:
        self.geometry[1] = snap_to_grid(y)

    def size(self) -> Point2D:
        return Point2D(self.width, self.height)

    def set_size(self, new_size: Point2D):
        self.width = new_size.x()
        self.height = new_size.y()

    def set_rect(self, new_rect: Rectangle):
        self.x = new_rect.x()
        self.y = new_rect.y()
        self.width = new_rect.width()
        self.height = new_rect.height()

    @property
    def time_created(self) -> datetime:
        return self.created

    @time_created.setter
    def time_created(self, new_dt: Union[datetime, str]):
        if isinstance(new_dt, datetime):
            self.created = new_dt.replace(microsecond=0)
        else:
            self.created = datetime_from_string(new_dt)

    @property
    def time_modified(self) -> datetime:
        return self.modified

    @time_modified.setter
    def time_modified(self, new_dt: Union[datetime, str]):
        if isinstance(new_dt, datetime):
            self.modified = new_dt.replace(microsecond=0)
        else:
            self.modified = datetime_from_string(new_dt)
