from dataclasses import field
from typing import List
from misli.basic_classes.color import Color
from misli.basic_classes.point2d import Point2D

from misli.entity_library import entity_type
from misli.entity_library.entity import Entity
from pamet.constants import DEFAULT_BG_COLOR, DEFAULT_COLOR

BEZIER_CUBIC = 'bezier_cubic'
DEFAULT_LINE_THICKNESS = 1.5


@entity_type
class Arrow(Entity):
    page_id: str = ''
    # not used if anchor/note is set
    tail_coords: list = field(default_factory=list)
    tail_note_id: str = None
    # top bottom left right (ATM). If empty - choose dynamically
    tail_anchor: str = None
    mid_point_coords: List[list] = field(default_factory=list)
    head_coords: list = field(default_factory=list)
    head_note_id: str = None
    head_anchor: str = None

    color: tuple = DEFAULT_COLOR
    # background_color: tuple = DEFAULT_BG_COLOR
    line_type: str = None
    line_thickness: float = DEFAULT_LINE_THICKNESS
    line_function_name: str = BEZIER_CUBIC
    head_shape: str = None
    tail_shape: str = None

    def __repr__(self):
        return '<Arrow id=%s>' % self.id

    def __post_init__(self):
        # self.type_name = type(self).__name__
        if not self.page_id:
            raise Exception

        # # Convert the tuples to points
        # if isinstance(self.tail_point, (tuple, list)):
        #     self.tail_point = Point2D(*self.tail_point)
        # if isinstance(self.head_point, (tuple, list)):
        #     self.head_point = Point2D(*self.head_point)
        # for idx, mid_point in enumerate(self.mid_points):
        #     if isinstance(mid_point, (tuple, list)):
        #         self.mid_points[idx] = Point2D(*mid_point)

    def gid(self):
        return self.page_id, self.id

    def parent_gid(self):
        return self.page_id

    @property
    def tail_point(self) -> Point2D:
        if not self.tail_coords:
            return None
        return Point2D(*self.tail_coords)

    @tail_point.setter
    def tail_point(self, point: Point2D):
        self.tail_coords = point.as_tuple()

    @property
    def head_point(self) -> Point2D:
        if not self.head_coords:
            return None
        return Point2D(*self.head_coords)

    @head_point.setter
    def head_point(self, point: Point2D):
        self.head_coords = point.as_tuple()

    @property
    def mid_points(self) -> List[Point2D]:
        return [Point2D(*mid_point) for mid_point in self.mid_point_coords]

    def get_midpoint(self, idx: int) -> Point2D:
        return Point2D(*self.mid_point_coords[idx])

    def replace_midpoints(self, midpoint_list: List[Point2D]):
        self.mid_point_coords = [mp.as_tuple() for mp in midpoint_list]

    # def asdict(self):
    #     self_dict = super().asdict()

    #     # Convert the points to tuples
    #     for point_name in ['tail_point', 'head_point']:
    #         point = self_dict[point_name]
    #         if point:
    #             self_dict[point_name] = point.as_tuple()

    #     mid_points = self_dict['mid_points']
    #     for idx, mid_point in enumerate(mid_points):
    #         mid_points[idx]

    #     self_dict['mid_points'] = [
    #         point.as_tuple() for point in self_dict['mid_points']
    #     ]

    #     return self_dict

    def get_color(self) -> Color:
        return Color(*self.color)

    def set_color(self, color: Color):
        self.color = color.as_tuple()
