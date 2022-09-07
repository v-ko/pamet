from copy import copy
from typing import Generator, List, Union

import fusion
from fusion.util import Point2D, Rectangle
from fusion.view import View
import pamet

from pamet.constants import ARROW_EDGE_RAIDUS, RESIZE_CIRCLE_RADIUS, ARROW_SELECTION_RADIUS
from pamet.desktop_app.util import control_is_pressed, shift_is_pressed
from pamet.constants import MOVE_SPEED, MIN_HEIGHT_SCALE, MAX_HEIGHT_SCALE

from pamet import actions
from pamet.actions import map_page as map_page_actions
from pamet.actions import tab as tab_actions
from pamet.model.arrow import ArrowAnchorType
from pamet.model.text_note import TextNote
from pamet.views.arrow.widget import ArrowView
from pamet.views.map_page.state import MapPageViewState, MapPageMode
from pamet.views.note.base.view import NoteView

log = fusion.get_logger(__name__)


class MapPageView(View):

    def __init__(self, parent, initial_state):
        super().__init__(initial_state=initial_state)
        self.parent_tab = parent

        self._state = initial_state
        self._left_mouse_is_pressed = False
        self._mouse_position_on_left_press = Point2D(0, 0)
        self._note_views_under_mouse = []

    def note_views(self) -> List[NoteView]:
        raise NotImplementedError

    def arrow_views(self) -> List[ArrowView]:
        raise NotImplementedError

    @property
    def page(self):
        return self.state().page.copy()

    @property
    def viewport(self):
        return self.state().viewport

    def get_note_view_state_for_note_gid(self, note_gid: str):
        for nv_state in self.state().note_view_states:
            if nv_state.note_gid == note_gid:
                return nv_state
        return None

    def get_note_views_in_area(self, rect: Rectangle):
        unprojected_rect = self.state().unproject_rect(rect)
        intersecting = []

        for child in self.note_views():
            if child.state().rect().intersects(unprojected_rect):
                intersecting.append(child)

        return intersecting

    def get_note_views_at(
            self,
            position: Point2D,
            radius: float = 0) -> Generator[NoteView, None, None]:
        unprojected_mouse_pos = self.state().unproject_point(position)

        for note_view in self.note_views():
            nv_rect = note_view.state().rect()
            if radius:
                # Instead of implementing a Rectangle.intersects(circle)
                # we expand the rectangle to do the same inference
                nv_rect: Rectangle = copy(nv_rect)
                nv_rect.set_size(nv_rect.size() +
                                 Point2D(radius * 2, radius * 2))
                nv_rect.set_top_left(nv_rect.top_left() -
                                     Point2D(radius, radius))

            if nv_rect.contains(unprojected_mouse_pos):
                yield note_view

    def get_note_view_at(self,
                         position: Point2D,
                         radius: float = 0) -> Union[NoteView, None]:
        for note_view in self.get_note_views_at(position, radius):
            return note_view
        return None

    def get_arrow_views_at(
            self, position: Point2D) -> Generator[ArrowView, None, None]:
        unprojected_pos = self.state().unproject_point(position)
        for arrow_view in self.arrow_views():
            if arrow_view.intersects_circle(unprojected_pos,
                                            ARROW_SELECTION_RADIUS):
                yield arrow_view

    def get_arrow_view_at(self, position: Point2D) -> Union[ArrowView, None]:
        for arrow_view in self.get_arrow_views_at(position):
            return arrow_view
        return None

    def resize_circle_intersect(self, position: Point2D):
        for nc in self.note_views():
            unprojected_pos = self.state().unproject_point(position)
            resize_circle_center = nc.state().rect().bottom_right()

            distance = resize_circle_center.distance_to(unprojected_pos)
            if distance <= RESIZE_CIRCLE_RADIUS:
                return nc

    def arrow_anchor_at(self, position: Point2D):
        """Returns a tuple (note_id, anchor_type) for the closest anchor"""
        unprojected_pos = self.state().unproject_point(position)

        # Get the note views close enough to the mouse to show anchors
        adjacent_note_views = self.get_note_views_at(position,
                                                     ARROW_EDGE_RAIDUS)

        # Get the note, anchor, distance tuples of the intersections
        intersections = []
        for note_view in adjacent_note_views:
            for anchor_type in ArrowAnchorType.real_types():
                note_vs = note_view.state()
                anchor_center = note_vs.arrow_anchor(anchor_type)
                distance = unprojected_pos.distance_to(anchor_center)
                intersections.append((note_view, anchor_type, distance))

        if not intersections:
            return None

        # Sort them and return the first
        intersections = sorted(intersections, key=lambda i: i[2])
        note_view, anchor_type = intersections[0][:2]
        return note_view.state().get_note().own_id, anchor_type

    def handle_delete_shortcut(self):
        map_page_actions.delete_selected_children(self.state())

    def handle_left_mouse_long_press(self, mouse_pos: Point2D):
        if self.state().mode() != MapPageMode.NONE:
            return

        nc_under_mouse = self.get_note_view_at(mouse_pos)
        arrow_view_under_mouse = self.get_arrow_view_at(mouse_pos)
        child_under_mouse = nc_under_mouse

        # If there's a note - prefer ignore the arrow
        if arrow_view_under_mouse and not nc_under_mouse:
            # Ignore  arrows that are not free floating on both sides
            av_state = arrow_view_under_mouse.state()
            if av_state.tail_coords and av_state.head_coords:
                child_under_mouse = arrow_view_under_mouse

        if child_under_mouse:
            state = self.state()
            if child_under_mouse.state() not in state.selected_children:
                map_page_actions.update_child_selections(
                    state, {child_under_mouse.state(): True})
            map_page_actions.start_child_move(self.state(), mouse_pos)

    def handle_left_mouse_press(self, mouse_pos: Point2D):
        self._mouse_position_on_left_press = copy(mouse_pos)
        self._left_mouse_is_pressed = True

        ctrl_pressed = control_is_pressed()
        shift_pressed = shift_is_pressed()
        state = self.state()
        unproj_mouse_pos = state.unproject_point(mouse_pos)

        child_under_mouse = self.get_arrow_view_at(mouse_pos)
        nv_under_mouse = self.get_note_view_at(mouse_pos)
        if nv_under_mouse:
            child_under_mouse = nv_under_mouse
        resize_nv = self.resize_circle_intersect(mouse_pos)

        if state.mode() == MapPageMode.CREATE_ARROW:
            anchor_props = self.arrow_anchor_at(mouse_pos)
            note_id, anchor_type = anchor_props or (None, ArrowAnchorType.NONE)
            map_page_actions.arrow_creation_click(state,
                                                  fixed_pos=unproj_mouse_pos,
                                                  anchor_note_id=note_id,
                                                  anchor_type=anchor_type)
            return

        if ctrl_pressed and shift_pressed:
            map_page_actions.start_drag_select(state, mouse_pos)
            return

        if ctrl_pressed and not shift_pressed:
            if child_under_mouse:
                nc_selected = child_under_mouse.state() in self.state(
                ).selected_children
                map_page_actions.update_child_selections(
                    state, {child_under_mouse.state(): not nc_selected})
        elif shift_pressed or (ctrl_pressed and shift_pressed):
            # Select the note under the mouse (if it's not already so)
            if child_under_mouse:
                nc_selected = child_under_mouse.state() in self.state(
                ).selected_children
                if not nc_selected:
                    map_page_actions.update_child_selections(
                        state, {child_under_mouse.state(): True})

        # Clear selection (or reduce it to the note under the mouse)
        if not ctrl_pressed and not shift_pressed:
            if resize_nv:
                child_under_mouse = resize_nv

            map_page_actions.clear_child_selection(state)

            if child_under_mouse:
                map_page_actions.update_child_selections(
                    state, {child_under_mouse.state(): True})

        # Check for resize initiation
        if resize_nv:
            resize_nv_state = resize_nv.state()
            if resize_nv_state not in state.selected_children:
                map_page_actions.update_child_selections(
                    state, {resize_nv_state: True})

            resize_circle_center = resize_nv_state.rect().bottom_right()
            rcc_projected = state.project_point(resize_circle_center)
            map_page_actions.start_notes_resize(state,
                                                resize_nv_state.get_note(),
                                                mouse_pos, rcc_projected)

    def handle_left_mouse_release(self, mouse_pos: Point2D):
        self._left_mouse_is_pressed = False

        state: MapPageViewState = self.state()
        mode = state.mode()
        unproj_mouse_pos = state.unproject_point(mouse_pos)

        if mode == MapPageMode.DRAG_SELECT:
            same_pos = state.mouse_position_on_drag_select_start == mouse_pos
            map_page_actions.stop_drag_select(state, mouse_pos)
            # If no drag select has happened, but it was just a click - add
            # the note under the mouse to the selection.
            if same_pos:
                child_under_mouse = self.get_arrow_view_at(mouse_pos)
                nv_under_mouse = self.get_note_view_at(mouse_pos)
                if nv_under_mouse:
                    child_under_mouse = nv_under_mouse
                map_page_actions.update_child_selections(
                    state, {child_under_mouse.state(): True})

        elif mode == MapPageMode.NOTE_RESIZE:
            new_size = self._new_note_size_on_resize(mouse_pos)
            map_page_actions.finish_notes_resize(self.state(), new_size)

        elif mode == MapPageMode.CHILD_MOVE:
            pos_delta = mouse_pos - state.mouse_position_on_note_drag_start
            pos_delta /= self.state().height_scale_factor()
            map_page_actions.finish_child_move(self.state(), pos_delta)

        elif mode == MapPageMode.DRAG_NAVIGATION:
            map_page_actions.finish_mouse_drag_navigation(self.state())
            tab_actions.update_current_url(self.parent_tab.state())

        elif mode == MapPageMode.ARROW_EDGE_DRAG:
            anchor_props = self.arrow_anchor_at(mouse_pos)
            note_id, anchor_type = anchor_props or (None, ArrowAnchorType.NONE)
            map_page_actions.finish_arrow_edge_drag(state,
                                                    fixed_pos=unproj_mouse_pos,
                                                    anchor_note_id=note_id,
                                                    anchor_type=anchor_type)

        elif mode == MapPageMode.NONE:
            note_view = self.get_note_view_at(mouse_pos)
            if note_view and control_is_pressed():
                note_view.middle_click_event(mouse_pos)

    def _new_note_size_on_resize(self, new_mouse_pos: Point2D) -> Point2D:
        mouse_delta = new_mouse_pos - self.state().note_resize_click_position
        size_delta = mouse_delta - self.state(
        ).note_resize_delta_from_note_edge

        size_delta = size_delta / self.state().height_scale_factor()
        new_size = self.state().note_resize_main_note.size() + size_delta

        return new_size

    def _handle_move_on_drag_select(self, mouse_pos: Point2D):
        selection_rect = Rectangle.from_points(
            self.state().mouse_position_on_drag_select_start, mouse_pos)
        unprojected_rect = self.state().unproject_rect(selection_rect)

        nvs_in_selection = self.get_note_views_in_area(selection_rect)
        arrow_views_in_selection = [
            av for av in self.arrow_views()
            if av.intersects_rect(unprojected_rect)
        ]
        drag_selected_children = set([
            child.state()
            for child in nvs_in_selection + arrow_views_in_selection
        ])

        map_page_actions.update_drag_select(self.state(),
                                            selection_rect.as_tuple(),
                                            drag_selected_children)

    def handle_mouse_move(self, mouse_pos: Point2D):
        state = self.state()
        mode = state.mode()
        delta = self._mouse_position_on_left_press - mouse_pos
        unproj_mouse_pos = state.unproject_point(mouse_pos)
        self._note_views_under_mouse = list(self.get_note_views_at(mouse_pos))

        if mode == MapPageMode.NONE:
            if self._left_mouse_is_pressed:
                map_page_actions.start_mouse_drag_navigation(
                    state, self._mouse_position_on_left_press, delta)

        if mode == MapPageMode.DRAG_SELECT:
            self._handle_move_on_drag_select(mouse_pos)

        elif mode == MapPageMode.NOTE_RESIZE:
            new_size = self._new_note_size_on_resize(mouse_pos)
            map_page_actions.resize_note_views(state, new_size)

        elif mode == MapPageMode.CHILD_MOVE:
            pos_delta = mouse_pos - self._mouse_position_on_left_press
            pos_delta /= state.height_scale_factor()
            map_page_actions.moved_child_view_update(state, pos_delta)

        elif mode == MapPageMode.DRAG_NAVIGATION:
            map_page_actions.mouse_drag_navigation_move(state, delta)

        elif mode == MapPageMode.CREATE_ARROW:
            anchor_props = self.arrow_anchor_at(mouse_pos)
            note_id, anchor_type = anchor_props or (None, ArrowAnchorType.NONE)
            map_page_actions.arrow_creation_move(state,
                                                 fixed_pos=unproj_mouse_pos,
                                                 anchor_note_id=note_id,
                                                 anchor_type=anchor_type)

        elif mode == MapPageMode.ARROW_EDGE_DRAG:
            anchor_props = self.arrow_anchor_at(mouse_pos)
            note_id, anchor_type = anchor_props or (None, ArrowAnchorType.NONE)
            map_page_actions.arrow_edge_drag_update(state,
                                                    fixed_pos=unproj_mouse_pos,
                                                    anchor_note_id=note_id,
                                                    anchor_type=anchor_type)

    def handle_mouse_scroll(self, steps: int):
        delta = MOVE_SPEED * steps
        current_height = self.state().viewport_height

        new_height = max(MIN_HEIGHT_SCALE,
                         min(current_height - delta, MAX_HEIGHT_SCALE))

        map_page_actions.set_viewport_height(self.state(), new_height)
        tab_actions.update_current_url(self.parent_tab.state())

    def left_mouse_double_click_event(self, mouse_pos: Point2D):
        if self.state().mode() == MapPageMode.CREATE_ARROW:
            map_page_actions.abort_special_mode(self.state())
            return

        note_view = self.get_note_view_at(mouse_pos)

        if note_view:
            # Map the mouse position on the note and call its virtual method
            note_rect: Rectangle = note_view.state().get_note().rect()
            mouse_pos_unproj = self.state().unproject_point(mouse_pos)
            relative_pos = note_rect.top_left() - mouse_pos_unproj
            note_view.left_mouse_double_click_event(relative_pos)
        else:
            note_pos = self.state().unproject_point(mouse_pos)
            note = TextNote().with_id(page_id=self.state().page_id)
            note.x = note_pos.x()
            note.y = note_pos.y()
            actions.note.create_new_note(self.parent_tab.state(), note)

    def middle_click_event(self, mouse_pos: Point2D):
        note_view = self.get_note_view_at(mouse_pos)

        if note_view:
            note_view.middle_click_event(mouse_pos)

    def handle_resize_event(self, new_size: Point2D):
        map_page_actions.resize_page(self.state(), new_size)

    def undo(self):
        pamet.undo_service().back_one_step(self.state().page_id)

    def redo(self):
        pamet.undo_service().forward_one_step(self.state().page_id)
