from dataclasses import field
from enum import Enum
from typing import List
from fusion.util.color import Color
from fusion.util.point2d import Point2D

from fusion.libs.entity import entity_type
from fusion.logging import get_logger

import pamet
from pamet.constants import DEFAULT_ARROW_THICKNESS
from pamet.constants import DEFAULT_BG_COLOR, DEFAULT_COLOR
from pamet.model.page_child import PageChild

log = get_logger(__name__)
BEZIER_CUBIC = 'bezier_cubic'


class ArrowAnchorType(Enum):
    NONE = 0
    AUTO = 1
    MID_LEFT = 2
    TOP_MID = 3
    MID_RIGHT = 4
    BOTTOM_MID = 5

    @classmethod
    def real_types(cls):
        yield from [cls.MID_LEFT, cls.TOP_MID, cls.MID_RIGHT, cls.BOTTOM_MID]


@entity_type
class Arrow(PageChild):
    tail_coords: list = field(default_factory=list)
    tail_note_id: str = None
    tail_anchor: str = ArrowAnchorType.NONE.name

    mid_point_coords: List[list] = field(default_factory=list)

    head_coords: list = field(default_factory=list)
    head_note_id: str = None
    head_anchor: str = ArrowAnchorType.NONE.name

    color: tuple = DEFAULT_COLOR
    # background_color: tuple = DEFAULT_BG_COLOR
    line_type: str = None
    line_thickness: float = DEFAULT_ARROW_THICKNESS
    line_function_name: str = BEZIER_CUBIC
    head_shape: str = None
    tail_shape: str = None

    def parent_gid(self):
        return self.page_id

    def get_parent_page(self):
        return pamet.page(self.page_id)

    @property
    def tail_point(self) -> Point2D:
        if not self.tail_coords:
            return None
        return Point2D(*self.tail_coords)

    @tail_point.setter
    def tail_point(self, point: Point2D):
        if point:
            self.tail_coords = point.as_tuple()
        else:
            self.tail_coords = None

    @property
    def head_point(self) -> Point2D:
        if not self.head_coords:
            return None
        return Point2D(*self.head_coords)

    @head_point.setter
    def head_point(self, point: Point2D):
        if point:
            self.head_coords = point.as_tuple()
        else:
            self.head_coords = None

    @property
    def mid_points(self) -> List[Point2D]:
        return [Point2D(*mid_point) for mid_point in self.mid_point_coords]

    def get_midpoint(self, idx: int) -> Point2D:
        return Point2D(*self.mid_point_coords[idx])

    def replace_midpoints(self, midpoint_list: List[Point2D]):
        self.mid_point_coords = [mp.as_tuple() for mp in midpoint_list]

    def get_color(self) -> Color:
        return Color(*self.color)

    def set_color(self, color: Color):
        self.color = color.as_tuple()

    @property
    def tail_anchor_type(self):
        return ArrowAnchorType[self.tail_anchor]

    @tail_anchor_type.setter
    def tail_anchor_type(self, new_type: ArrowAnchorType):
        self.tail_anchor = new_type.name

    @property
    def head_anchor_type(self):
        return ArrowAnchorType[self.head_anchor]

    @head_anchor_type.setter
    def head_anchor_type(self, new_type: ArrowAnchorType):
        self.head_anchor = new_type.name

    def has_tail_anchor(self):
        return bool(self.tail_note_id)

    def has_head_anchor(self):
        return bool(self.head_note_id)

    def edge_indices(self):
        mid_edge_count = 2 + len(self.mid_points)
        return list(range(mid_edge_count))

    def potential_edge_indices(self):
        return [i + 0.5 for i in self.edge_indices()[:-1]]

    def all_edge_indices(self):
        return sorted(self.edge_indices() + self.potential_edge_indices())

    def set_tail(self,
                 fixed_pos: Point2D = None,
                 anchor_note_id: str = None,
                 anchor_type: ArrowAnchorType = ArrowAnchorType.NONE):
        if fixed_pos and anchor_note_id:
            # The fixed pos is almost always propagated
            # but if there's an anchor note - it takes precedence
            fixed_pos = None

        if fixed_pos and anchor_type != ArrowAnchorType.NONE:
            raise Exception

        self.tail_point = fixed_pos
        self.tail_note_id = anchor_note_id
        self.tail_anchor_type = anchor_type

    def set_head(self,
                 fixed_pos: Point2D = None,
                 anchor_note_id: str = None,
                 anchor_type: ArrowAnchorType = ArrowAnchorType.NONE):
        if fixed_pos and anchor_note_id:
            # The fixed pos is almost always propagated
            # but if there's an anchor note - it takes precedence
            fixed_pos = None

        if fixed_pos and anchor_type != ArrowAnchorType.NONE:
            raise Exception

        self.head_point = fixed_pos
        self.head_note_id = anchor_note_id
        self.head_anchor_type = anchor_type
