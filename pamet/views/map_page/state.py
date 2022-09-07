from __future__ import annotations

from dataclasses import field
from enum import Enum
from typing import List

import pamet
from fusion.util import Rectangle, Point2D
from fusion.libs.state import view_state_type, ViewState
from pamet.constants import DEFAULT_EYE_HEIGHT
from pamet.util.url import Url
from pamet.model.note import Note
from pamet.model.page import Page
from pamet.views.arrow.widget import ArrowViewState
from pamet.views.map_page.viewport import Viewport
from pamet.views.note.base.state import NoteViewState


class MapPageMode(Enum):
    NONE = 0
    DRAG_NAVIGATION = 1
    DRAG_SELECT = 2
    NOTE_RESIZE = 3
    CHILD_MOVE = 4
    CREATE_ARROW = 5
    ARROW_EDGE_DRAG = 6


@view_state_type
class MapPageViewState(ViewState, Viewport, Page):
    # page_id: str = ''
    note_view_states: set[NoteViewState] = field(default_factory=set)
    arrow_view_states: set[ArrowViewState] = field(default_factory=set)

    geometry: Rectangle = Rectangle(0, 0, 500, 500)
    viewport_center: Point2D = field(default_factory=Point2D)
    viewport_height: float = DEFAULT_EYE_HEIGHT

    special_mode: int = 0

    # drag_navigation_active: bool = False
    drag_navigation_start_position: Point2D = None

    selected_children: set = field(default_factory=set)

    # Field/drag selection
    mouse_position_on_drag_select_start: Point2D = None
    drag_selected_children: set = field(default_factory=set)
    drag_select_rect_props: list = field(default_factory=list)

    # Note resize related
    mouse_position_on_note_drag_start: Point2D = None
    note_resize_click_position: Point2D = None
    note_resize_delta_from_note_edge: Point2D = None
    note_resize_main_note: Note = None
    viewport_position_on_press: Point2D = None
    note_resize_states: List[NoteViewState] = field(default_factory=list)

    # Note move related
    moved_note_states: List[NoteViewState] = field(default_factory=list)
    moved_arrow_states: List[ArrowViewState] = field(default_factory=list)

    # Arrow manipulation related
    new_arrow_view_states: List[ArrowViewState] = field(default_factory=list)
    arrow_with_visible_cps: ArrowViewState = None
    dragged_edge_index: float = None

    def __repr__(self):
        return (f'<MapPageViewState page_id={self.page_id}'
                f' {len(self.note_view_states)=}>')

    @property
    def page_id(self):
        return self.id

    def mode(self):
        return MapPageMode(self.special_mode)

    def set_mode(self, mode: MapPageMode):
        if self.mode() != MapPageMode.NONE:
            self.clear_mode()
        self.special_mode = mode.value

    def clear_mode(self):
        self.special_mode = MapPageMode.NONE
        self.drag_navigation_start_position = None
        self.mouse_position_on_drag_select_start = None
        self.drag_selected_children = set()
        self.drag_select_rect_props = []

        self.mouse_position_on_note_drag_start = None
        self.note_resize_click_position = None
        self.note_resize_delta_from_note_edge = None
        self.note_resize_main_note = None
        self.viewport_position_on_press = None
        self.note_resize_states.clear()

        self.moved_note_states.clear()
        self.moved_arrow_states.clear()

        self.new_arrow_view_states.clear()

    def view_state_for_note_own_id(self, note_own_id: str):
        for note_vs in self.note_view_states:
            if note_vs.note_gid == (self.page_id, note_own_id):
                return note_vs
        return None

    def url(self):
        return Url(f'pamet:///p/{self.page_id}')

    def page_url(self, with_anchor=True) -> Url:
        url = self.url()
        center = self.viewport_center

        if with_anchor:
            url = url.with_anchor(eye_pos=center,
                                  eye_height=self.viewport_height)

        return url
