from __future__ import annotations

from typing import Generator, List, Union
from dataclasses import field
from datetime import datetime

from misli import get_logger
from misli import Entity, entity_type
from misli.helpers import datetime_from_string
from misli.basic_classes import Point2D, Rectangle, Color

import pamet
from pamet.constants import DEFAULT_NOTE_HEIGHT, DEFAULT_NOTE_WIDTH
from pamet.constants import DEFAULT_BG_COLOR, DEFAULT_COLOR
from pamet.constants import MIN_NOTE_WIDTH, MIN_NOTE_HEIGHT
from pamet.constants import MAX_NOTE_WIDTH, MAX_NOTE_HEIGHT
from pamet.helpers import Url
from pamet.model.arrow import Arrow, ArrowAnchorType

log = get_logger(__name__)

URL = 'url'


@entity_type
class Note(Entity):
    page_id: str = ''
    geometry: list = field(default_factory=lambda:
                           [0, 0, DEFAULT_NOTE_WIDTH, DEFAULT_NOTE_HEIGHT])
    color: tuple = field(default_factory=lambda: DEFAULT_COLOR)
    background_color: tuple = field(default_factory=lambda: DEFAULT_BG_COLOR)
    content: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
    created: datetime = field(
        default_factory=lambda: datetime.fromtimestamp(0))
    modified: datetime = field(
        default_factory=lambda: datetime.fromtimestamp(0))
    tags: List[str] = field(default_factory=list)
    type_name: str = ''

    def __repr__(self):
        return f'<{type(self).__name__} id={self.id}>'

    def __post_init__(self):
        self.type_name = type(self).__name__
        if not self.page_id:
            log.warning('Initializing Note without a page_id')

    def asdict(self):
        self_dict = super().asdict()
        self_dict['type_name'] = type(self).__name__
        return self_dict

    def gid(self):
        return self.page_id, self.id

    def parent_gid(self):
        return self.page_id

    def get_page(self):
        return pamet.page(id=self.page_id)

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
    def y(self, y: float) -> float:
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

    # @property
    # def time_created(self) -> datetime:
    #     return self.created

    # @time_created.setter
    # def time_created(self, new_dt: Union[datetime, str]):
    #     if isinstance(new_dt, datetime):
    #         self.created = new_dt.replace(microsecond=0)
    #     else:
    #         self.created = datetime_from_string(new_dt)

    # @property
    # def time_modified(self) -> datetime:
    #     return self.modified

    # @time_modified.setter
    # def time_modified(self, new_dt: Union[datetime, str]):
    #     if isinstance(new_dt, datetime):
    #         self.modified = new_dt.replace(microsecond=0)
    #     else:
    #         self.modified = datetime_from_string(new_dt)

    @property
    def url(self) -> Url:
        return Url(self.content.get(URL, ''))

    @url.setter
    def url(self, new_url: Union[Url, str, None]):
        if isinstance(new_url, Url):
            new_url = str(new_url)
        # If None is passed - remove the URL parameter (may be unnecessary)
        elif new_url is None:
            self.content.pop(URL, None)
            return
        self.content[URL] = new_url

    def in_arrows(self) -> Generator[Arrow, None, None]:
        arrows = pamet.page(id=self.page_id).arrows()
        for arrow in arrows:
            if self.id == arrow.head_note_id:
                yield arrow

    def out_arrows(self) -> Generator[Arrow, None, None]:
        arrows = pamet.page(id=self.page_id).arrows()
        for arrow in arrows:
            if self.id == arrow.tail_note_id:
                yield arrow

    def connected_arrows(self) -> Generator[Arrow, None, None]:
        arrows = pamet.page(id=self.page_id).arrows()
        for arrow in arrows:
            if self.id == arrow.tail_note_id or self.id == arrow.head_note_id:
                yield arrow

    def arrow_anchor(self, anchor_type: ArrowAnchorType) -> Point2D:
        """Returns the center position for a specific arrow anchor.

        Raises: Does not support the ArrowAnchorType.AUTO
        """
        rect: Rectangle = self.rect()

        match anchor_type:
            case ArrowAnchorType.MID_LEFT:
                return rect.top_left() + Point2D(0, rect.height() / 2)
            case ArrowAnchorType.TOP_MID:
                return rect.top_left() + Point2D(rect.width() / 2, 0)
            case ArrowAnchorType.MID_RIGHT:
                return rect.top_right() + Point2D(0, rect.height() / 2)
            case ArrowAnchorType.BOTTOM_MID:
                return rect.bottom_left() + Point2D(rect.width() / 2)
            case _:
                raise Exception
