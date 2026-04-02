from dataclasses import field
from enum import Enum
from typing import List, TypedDict

from fusion.libs.entity import entity_type
from fusion.logging import get_logger
from fusion.util.point2d import Point2D

from pamet.constants import DEFAULT_ARROW_THICKNESS, DEFAULT_COLOR_ROLE
from pamet.model.page_child import PageChild

log = get_logger(__name__)
BEZIER_CUBIC = "bezier_cubic"


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


class EndPointProps(TypedDict):
    position: list | None
    note_anchor_id: str | None
    note_anchor_type: str


class ArrowStyle(TypedDict):
    color_role: str
    line_type: str
    thickness: float
    line_function: str
    head_shape: str
    tail_shape: str


_DEFAULT_ENDPOINT: EndPointProps = {
    "position": None,
    "note_anchor_id": None,
    "note_anchor_type": "none",
}

_DEFAULT_ARROW_STYLE: ArrowStyle = {
    "color_role": DEFAULT_COLOR_ROLE,
    "line_type": "solid",
    "thickness": DEFAULT_ARROW_THICKNESS,
    "line_function": BEZIER_CUBIC,
    "head_shape": "arrow",
    "tail_shape": "arrow",
}


@entity_type
class Arrow(PageChild):
    """Arrow connecting notes on a page.

    Sub-object shapes defined by EndPointProps and ArrowStyle TypedDicts.
    Matches TS ArrowData structure (snake_case wire format).
    """

    tail: EndPointProps = field(default_factory=lambda: _DEFAULT_ENDPOINT.copy())
    head: EndPointProps = field(default_factory=lambda: _DEFAULT_ENDPOINT.copy())
    mid_points: List[list] = field(default_factory=list)
    style: ArrowStyle = field(default_factory=lambda: _DEFAULT_ARROW_STYLE.copy())

    # --- Tail convenience properties ---
    @property
    def tail_point(self) -> Point2D | None:
        pos = self.tail["position"]
        if not pos:
            return None
        return Point2D(*pos)

    @tail_point.setter
    def tail_point(self, point: Point2D | None):
        self.tail["position"] = list(point.as_tuple()) if point else None

    @property
    def tail_note_id(self) -> str | None:
        return self.tail["note_anchor_id"]

    @tail_note_id.setter
    def tail_note_id(self, nid: str | None):
        self.tail["note_anchor_id"] = nid

    @property
    def tail_anchor_type(self) -> ArrowAnchorType:
        name = (self.tail["note_anchor_type"] or "none").upper()
        return ArrowAnchorType[name]

    @tail_anchor_type.setter
    def tail_anchor_type(self, new_type: ArrowAnchorType):
        self.tail["note_anchor_type"] = new_type.name.lower()

    # --- Head convenience properties ---
    @property
    def head_point(self) -> Point2D | None:
        pos = self.head["position"]
        if not pos:
            return None
        return Point2D(*pos)

    @head_point.setter
    def head_point(self, point: Point2D | None):
        self.head["position"] = list(point.as_tuple()) if point else None

    @property
    def head_note_id(self) -> str | None:
        return self.head["note_anchor_id"]

    @head_note_id.setter
    def head_note_id(self, nid: str | None):
        self.head["note_anchor_id"] = nid

    @property
    def head_anchor_type(self) -> ArrowAnchorType:
        name = (self.head["note_anchor_type"] or "none").upper()
        return ArrowAnchorType[name]

    @head_anchor_type.setter
    def head_anchor_type(self, new_type: ArrowAnchorType):
        self.head["note_anchor_type"] = new_type.name.lower()

    # --- Style convenience ---
    @property
    def color_role(self) -> str:
        return self.style.get("color_role", DEFAULT_COLOR_ROLE)

    @color_role.setter
    def color_role(self, role: str):
        self.style["color_role"] = role

    @property
    def line_thickness(self) -> float:
        return self.style.get("thickness", DEFAULT_ARROW_THICKNESS)

    @line_thickness.setter
    def line_thickness(self, val: float):
        self.style["thickness"] = val

    # --- Mid-points ---
    def get_midpoints(self) -> List[Point2D]:
        return [Point2D(*mp) for mp in self.mid_points]

    def get_midpoint(self, idx: int) -> Point2D:
        return Point2D(*self.mid_points[idx])

    def replace_midpoints(self, midpoint_list: List[Point2D]):
        self.mid_points = [list(mp.as_tuple()) for mp in midpoint_list]

    # --- Anchor helpers ---
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

    def set_tail(
        self,
        fixed_pos: Point2D | None,
        anchor_note_id: str | None,
        anchor_type: ArrowAnchorType,
    ):
        if bool(fixed_pos) == bool(anchor_note_id):
            raise ValueError("Exactly one of fixed_pos or anchor_note_id must be set")

        if fixed_pos and anchor_type != ArrowAnchorType.NONE:
            raise ValueError("fixed_pos requires anchor_type == NONE")

        self.tail_point = fixed_pos
        self.tail_note_id = anchor_note_id
        self.tail_anchor_type = anchor_type

    def set_head(
        self,
        fixed_pos: Point2D | None,
        anchor_note_id: str | None,
        anchor_type: ArrowAnchorType,
    ):
        if bool(fixed_pos) == bool(anchor_note_id):
            raise ValueError("Exactly one of fixed_pos or anchor_note_id must be set")

        if fixed_pos and anchor_type != ArrowAnchorType.NONE:
            raise ValueError("fixed_pos requires anchor_type == NONE")

        self.head_point = fixed_pos
        self.head_note_id = anchor_note_id
        self.head_anchor_type = anchor_type
