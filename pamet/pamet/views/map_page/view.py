from copy import copy
from enum import Enum
from dataclasses import field
from typing import List

import misli
from misli.basic_classes import Point2D, Rectangle
from misli.entity_library.change import Change
from misli.gui import ViewState, view_state_type
from misli.gui.actions_library import action
from misli.gui.view_library.view import View
from misli.gui.views.context_menu.widget import ContextMenuWidget

import pamet
from pamet.constants import RESIZE_CIRCLE_RADIUS
from pamet.desktop_app.helpers import control_is_pressed, shift_is_pressed
from pamet.constants import MOVE_SPEED, MIN_HEIGHT_SCALE, MAX_HEIGHT_SCALE
from pamet.constants import INITIAL_EYE_Z
from pamet.model import Note

from pamet import actions
from pamet.views.map_page.viewport import Viewport
from pamet.views.note.base_note_view import NoteViewState

log = misli.get_logger(__name__)


class MapPageMode(Enum):
    NONE = 0
    DRAG_NAVIGATION = 1
    DRAG_SELECT = 2
    NOTE_RESIZE = 3
    NOTE_DRAG = 4


@view_state_type
class MapPageViewState(ViewState, Viewport):
    page_id: str = ''
    note_view_states: List[NoteViewState] = field(default_factory=list)
    geometry: Rectangle = Rectangle(0, 0, 500, 500)
    viewport_center: Point2D = field(default_factory=Point2D)
    viewport_height: float = INITIAL_EYE_Z

    selected_nc_ids: set = field(default_factory=set)

    drag_navigation_active: bool = False
    drag_navigation_start_position: Point2D = field(default_factory=Point2D)

    drag_select_active: bool = False
    mouse_position_on_drag_select_start: Point2D = field(
        default_factory=Point2D)
    drag_selected_nc_ids: list = field(default_factory=list)
    drag_select_rect_props: list = field(default_factory=list)

    note_resize_active: bool = False
    mouse_position_on_note_drag_start: Point2D = field(default_factory=Point2D)
    note_resize_click_position: Point2D = field(default_factory=Point2D)
    note_resize_delta_from_note_edge: Point2D = field(default_factory=Point2D)
    note_resize_main_note: Note = None
    viewport_position_on_press: Point2D = field(default_factory=Point2D)

    note_drag_active: bool = False

    # def __post_init__(self):
    #     self.viewport = Viewport(self)

    def __repr__(self):
        return (f'<MapPageViewState page_id={self.page_id}'
                f' {len(self.note_view_states)=}>')

    @property
    def viewport(self):
        return self

    # @property
    # def name(self):
    #     return self.page.name

    @property
    def page(self):
        return pamet.page(gid=self.page_id)

    def mode(self):  # TODO: this is not very elegant
        modes_sum = (self.drag_navigation_active + self.drag_select_active +
                     self.note_resize_active + self.note_drag_active)

        if not modes_sum:
            return MapPageMode.NONE

        elif modes_sum > 1:
            raise Exception('More than one mode activated')

        if self.drag_navigation_active:
            return MapPageMode.DRAG_NAVIGATION

        elif self.drag_select_active:
            return MapPageMode.DRAG_SELECT

        elif self.note_resize_active:
            return MapPageMode.NOTE_RESIZE

        elif self.note_drag_active:
            return MapPageMode.NOTE_DRAG


class MapPageView(View):

    def __init__(self, parent, initial_state):
        super().__init__(initial_state=initial_state)
        self._state = initial_state
        self._left_mouse_is_pressed = False
        self._mouse_position_on_left_press = Point2D(0, 0)
        self.parent_tab = parent

    def get_children(self) -> List[View]:
        raise NotImplementedError

    @action('MapPageView.handle_page_change')
    def handle_page_change(self, change: Change):
        if change.updated.name:
            tab_state = self.tab_widget.state()
            tab_state.title = change.last_state().name
            misli.gui.update_state(tab_state)

    @property
    def page(self):
        return self.state().page.copy()

    @property
    def viewport(self):
        return self.state().viewport

    def get_note_views_in_area(self, rect: Rectangle):
        unprojected_rect = self.viewport.unproject_rect(rect)
        intersecting = []

        for child in self.get_children():
            if child.state().note.rect().intersects(unprojected_rect):
                intersecting.append(child)

        return intersecting

    def get_note_views_at(self, position: Point2D):
        unprojected_mouse_pos = self.viewport.unproject_point(position)
        intersecting = []

        for child in self.get_children():
            if child.state().rect().contains(unprojected_mouse_pos):
                intersecting.append(child)

        return intersecting

    def get_note_view_at(self, position: Point2D):
        intersecting = self.get_note_views_at(position)
        if not intersecting:
            return None

        return intersecting[0]

    def resize_circle_intersect(self, position: Point2D):
        for nc in self.get_children():
            unprojected_pos = self.viewport.unproject_point(position)
            resize_circle_center = nc.state().rect().bottom_right()

            distance = resize_circle_center.distance_to(unprojected_pos)
            if distance <= RESIZE_CIRCLE_RADIUS:
                return nc

    def handle_delete_shortcut(self):
        actions.map_page.delete_selected_notes(self.id)

    def handle_left_mouse_long_press(self, mouse_pos: Point2D):
        if self.state().note_resize_active:
            return

        ncs_under_mouse = self.get_note_views_at(mouse_pos)
        if ncs_under_mouse:
            actions.map_page.start_note_drag(self.id, mouse_pos.as_tuple())

    def handle_left_mouse_press(self, mouse_pos: Point2D):
        self._mouse_position_on_left_press = copy(mouse_pos)
        self._left_mouse_is_pressed = True

        ctrl_pressed = control_is_pressed()
        shift_pressed = shift_is_pressed()

        nc_under_mouse = None
        ncs_under_mouse = self.get_note_views_at(mouse_pos)
        if ncs_under_mouse:
            nc_under_mouse = ncs_under_mouse[0]

        resize_nc = self.resize_circle_intersect(mouse_pos)

        if ctrl_pressed and shift_pressed:
            actions.map_page.start_drag_select(self.id, mouse_pos.as_tuple())
            return

        if ctrl_pressed:
            if nc_under_mouse:
                nc_selected = nc_under_mouse.id in self.state().selected_nc_ids
                actions.map_page.update_note_selections(
                    self.id, {nc_under_mouse.id: not nc_selected})

        # Clear selection (or reduce it to the note under the mouse)
        if not ctrl_pressed and not shift_pressed:
            if resize_nc:
                nc_under_mouse = resize_nc

            actions.map_page.clear_note_selection(self.id)

            if nc_under_mouse:
                actions.map_page.update_note_selections(
                    self.id, {nc_under_mouse.id: True})

        # Check for resize initiation
        if resize_nc:
            if resize_nc.id not in self.state().selected_nc_ids:
                actions.map_page.update_note_selections(
                    self.id, {resize_nc.id: True})

            resize_circle_center = resize_nc.state().rect().bottom_right()
            rcc_projected = self.viewport.project_point(resize_circle_center)
            actions.map_page.start_notes_resize(self.id,
                                                resize_nc.state().note,
                                                mouse_pos, rcc_projected)

            return

    def handle_right_mouse_press(self, position):
        ncs_under_mouse = self.get_note_views_at(position)
        if ncs_under_mouse:
            pass

        menu_entries = {
            'New note': pamet.commands.create_new_note,
            'New page': pamet.commands.create_new_page,
        }
        # Open the context menu with the tab as its parent
        context_menu = ContextMenuWidget(self.parent(), entries=menu_entries)
        context_menu.popup_on_mouse_pos()

    def handle_left_mouse_release(self, mouse_pos: Point2D):
        self._left_mouse_is_pressed = False

        state: MapPageViewState = self.state()
        mode = state.mode()

        if state.drag_select_active:
            actions.map_page.stop_drag_select(self.id)

        elif state.note_resize_active:
            new_size = self._new_note_size_on_resize(mouse_pos)
            actions.map_page.stop_notes_resize(self.id, new_size,
                                               state.selected_nc_ids)

        elif state.note_drag_active:
            pos_delta = mouse_pos - state.mouse_position_on_note_drag_start
            pos_delta /= self.viewport.height_scale_factor()
            actions.map_page.stop_note_drag(self.id, state.selected_nc_ids,
                                            pos_delta.as_tuple())

        elif mode == MapPageMode.DRAG_NAVIGATION:
            actions.map_page.stop_drag_navigation(self.id)

    def _new_note_size_on_resize(self, new_mouse_pos: Point2D) -> Point2D:
        mouse_delta = new_mouse_pos - self.state().note_resize_click_position
        size_delta = mouse_delta - self.state(
        ).note_resize_delta_from_note_edge

        size_delta = size_delta / self.viewport.height_scale_factor()
        new_size = self.state().note_resize_main_note.size() + size_delta

        return new_size

    def _handle_move_on_drag_select(self, mouse_pos: Point2D):
        selection_rect = Rectangle.from_points(
            self.state().mouse_position_on_drag_select_start, mouse_pos)

        ncs_in_selection = self.get_note_views_in_area(selection_rect)
        drag_selected_nc_ids = [nc.id for nc in ncs_in_selection]

        actions.map_page.update_drag_select(self.id, selection_rect.as_tuple(),
                                            drag_selected_nc_ids)

    def handle_mouse_move(self, mouse_pos: Point2D):
        state = self.state()
        mode = state.mode()
        delta = self._mouse_position_on_left_press - mouse_pos

        if mode == MapPageMode.NONE:
            if self._left_mouse_is_pressed:
                actions.map_page.start_mouse_drag_navigation(
                    self.id, self._mouse_position_on_left_press, delta)

        if mode == MapPageMode.DRAG_SELECT:
            self._handle_move_on_drag_select(mouse_pos)

        elif mode == MapPageMode.NOTE_RESIZE:
            new_size = self._new_note_size_on_resize(mouse_pos)
            actions.map_page.resize_note_views(new_size, state.selected_nc_ids)

        elif mode == MapPageMode.NOTE_DRAG:
            pos_delta = mouse_pos - self._mouse_position_on_left_press
            print(f'{self._mouse_position_on_left_press=}')
            pos_delta /= self.viewport.height_scale_factor()
            actions.map_page.note_drag_nc_position_update(
                state.selected_nc_ids, pos_delta)

        elif mode == MapPageMode.DRAG_NAVIGATION:
            actions.map_page.mouse_drag_navigation_move(self.id, delta)

    def handle_mouse_scroll(self, steps: int):
        delta = MOVE_SPEED * steps
        current_height = self.state().viewport_height

        new_height = max(MIN_HEIGHT_SCALE,
                         min(current_height - delta, MAX_HEIGHT_SCALE))

        actions.map_page.set_viewport_height(self.id, new_height)

    def handle_left_mouse_double_click(self, mouse_pos: Point2D):
        note_view = self.get_note_view_at(mouse_pos)

        if note_view:
            actions.note.start_editing_note(self.parent_tab.state(),
                                            note_view.state().note)
        else:
            actions.note.create_new_note(self.parent_tab.state(), mouse_pos)

    def handle_resize_event(self, width, height):
        actions.map_page.resize_page(self.id, width, height)
