from __future__ import annotations

from datetime import datetime
from typing import TypedDict, cast

import attrs
from fusion import entity_type, get_logger
from fusion.util import Point2D, Rectangle, current_time, timestamp

from pamet.constants import (
    DEFAULT_BG_COLOR_ROLE,
    DEFAULT_COLOR_ROLE,
    DEFAULT_NOTE_HEIGHT,
    DEFAULT_NOTE_WIDTH,
    MAX_NOTE_HEIGHT,
    MAX_NOTE_WIDTH,
    MIN_NOTE_HEIGHT,
    MIN_NOTE_WIDTH,
)
from pamet.model.page_child import PageChild

log = get_logger(__name__)


class ImageReference(TypedDict, total=False):
    id: str
    path: str
    width: int
    height: int


class PageReference(TypedDict, total=False):
    id: str
    path: str


class NoteContent(TypedDict, total=False):
    text: str
    url: str
    page_ref: PageReference
    image: ImageReference


class NoteStyle(TypedDict, total=False):
    color_role: str
    background_color_role: str


class NoteMetadata(TypedDict, total=False):
    is_project_index_header: bool


@entity_type
class Note(PageChild):
    geometry: list = attrs.Factory(
        lambda: [0, 0, DEFAULT_NOTE_WIDTH, DEFAULT_NOTE_HEIGHT]
    )
    style: NoteStyle = attrs.Factory(lambda: cast(NoteStyle, {}))
    content: NoteContent = attrs.Factory(lambda: cast(NoteContent, {}))
    metadata: NoteMetadata = attrs.Factory(lambda: cast(NoteMetadata, {}))
    created: str = attrs.Factory(lambda: timestamp(current_time()))
    modified: str = attrs.Factory(lambda: timestamp(current_time()))

    def __repr__(self):
        return f"<{type(self).__name__} id={self.id}>"

    def rect(self) -> Rectangle:
        return Rectangle(*self.geometry)

    @property
    def color_role(self) -> str:
        return self.style.get("color_role", DEFAULT_COLOR_ROLE)

    @color_role.setter
    def color_role(self, role: str):
        self.style["color_role"] = role

    @property
    def background_color_role(self) -> str:
        return self.style.get("background_color_role", DEFAULT_BG_COLOR_ROLE)

    @background_color_role.setter
    def background_color_role(self, role: str):
        self.style["background_color_role"] = role

    @property
    def width(self) -> float:
        return self.geometry[2]

    @width.setter
    def width(self, width: float):
        width = min(MAX_NOTE_WIDTH, max(width, MIN_NOTE_WIDTH))
        self.geometry[2] = width

    @property
    def height(self) -> float:
        return self.geometry[3]

    @height.setter
    def height(self, height: float):
        height = min(MAX_NOTE_HEIGHT, max(height, MIN_NOTE_HEIGHT))
        self.geometry[3] = height

    @property
    def x(self) -> float:
        return self.geometry[0]

    @x.setter
    def x(self, x: float):
        self.geometry[0] = x

    @property
    def y(self) -> float:
        return self.geometry[1]

    @y.setter
    def y(self, y: float):
        self.geometry[1] = y

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
    def datetime_created(self) -> datetime:
        return datetime.fromisoformat(self.created)

    @datetime_created.setter
    def datetime_created(self, new_dt: datetime):
        self.created = timestamp(new_dt)

    @property
    def datetime_modified(self) -> datetime:
        return datetime.fromisoformat(self.modified)

    @datetime_modified.setter
    def datetime_modified(self, new_dt: datetime):
        self.modified = timestamp(new_dt)
