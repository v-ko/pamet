import misli
import misli_gui

from misli import dataclasses
from misli.basic_classes import Point, Rectangle
from misli.constants import MOVE_SPEED, MIN_HEIGHT_SCALE, MAX_HEIGHT_SCALE
from misli.constants import RESIZE_CIRCLE_RADIUS

from misli_gui.base_component import Component
from misli_qt.helpers import control_is_pressed, shift_is_pressed

from pamet.note_components import usecases as notes_usecases
from pamet.map_page import usecases
from pamet.entities import Note
from pamet.map_page.viewport import Viewport

log = misli.get_logger(__name__)


@dataclasses.dataclass
class MapPageComponent(Component):
    def __init__(self, parent_id: str):
        Component.__init__(self, parent_id, obj_class='MapPage')

        self.viewport = Viewport(self)
        self.left_mouse_is_pressed = False
        self.mouse_position_on_left_press = Point(0, 0)
        self.selected_nc_ids = set()
        self.viewport_position_on_press = Point(0, 0)

        self.mouse_drag_navigation_active = False

        self.drag_select_active = False
        self.drag_select_nc_ids = []
        self.drag_select_rect_props = []

        self.note_resize_active = False
        self._note_resize_click_position = None
        self._note_resize_delta_from_note_edge = None
        self._note_resize_main_note = None

        self.note_drag_active = False

    def _handle_delete_shortcut(self):
        usecases.delete_selected_notes(self.id)

    def get_note_components_in_area(self, rect: Rectangle):
        unprojected_rect = self.viewport.unproject_rect(rect)
        intersecting = []

        for child in self.get_children():
            note = child.note()

            if note.rect().intersects(unprojected_rect):
                intersecting.append(child)

        return intersecting

    def get_note_components_at(self, position: Point):
        unprojected_mouse_pos = self.viewport.unproject_point(position)
        intersecting = []

        for child in self.get_children():
            note = child.note()

            if note.rect().contains(unprojected_mouse_pos):
                intersecting.append(child)

        return intersecting

    def get_note_component_at(self, position: Point):
        intersecting = self.get_note_components_at(position)
        if not intersecting:
            return None

        return intersecting[0]

    def resize_circle_intersect(self, position: Point):
        for nc in self.get_children():
            if nc.id not in self.selected_nc_ids:
                continue

            unprojected_pos = self.viewport.unproject_point(position)
            resize_circle_center = nc.note().rect().bottom_right()

            distance = resize_circle_center.distance_to(unprojected_pos)
            if distance <= RESIZE_CIRCLE_RADIUS:
                return nc

    def handle_left_mouse_long_press(self, mouse_pos: Point):
        ncs_under_mouse = self.get_note_components_at(mouse_pos)
        if ncs_under_mouse:
            usecases.start_note_drag(self.id, mouse_pos.to_list())

    def handle_left_mouse_press(self, mouse_pos: Point):
        self.mouse_position_on_left_press = mouse_pos
        self.left_mouse_is_pressed = True
        self.viewport_position_on_press = self.viewport.center()

        ctrl_pressed = control_is_pressed()
        shift_pressed = shift_is_pressed()

        nc_under_mouse = None
        ncs_under_mouse = self.get_note_components_at(mouse_pos)
        if ncs_under_mouse:
            nc_under_mouse = ncs_under_mouse[0]

        resize_nc = self.resize_circle_intersect(mouse_pos)

        if ctrl_pressed and shift_pressed:
            usecases.start_drag_select(self.id, mouse_pos.to_list())
            return

        if ctrl_pressed:
            if nc_under_mouse:
                nc_selected = nc_under_mouse.id in self.selected_nc_ids
                usecases.update_note_selections(
                    self.id, {nc_under_mouse.id: not nc_selected})

        # Clear selection (or reduce it to the note under the mouse)
        if not ctrl_pressed and not shift_pressed:
            if resize_nc:
                nc_under_mouse = resize_nc

            usecases.clear_note_selection(self.id)

            if nc_under_mouse:
                usecases.update_note_selections(
                    self.id, {nc_under_mouse.id: True})

        # Check for resize initiation
        if resize_nc:
            if resize_nc.id not in self.selected_nc_ids:
                usecases.update_note_selections(self.id, {resize_nc.id: True})

            resize_circle_center = resize_nc.note().rect().bottom_right()
            rcc_projected = self.viewport.project_point(resize_circle_center)
            self._note_resize_delta_from_note_edge = rcc_projected - mouse_pos
            self._note_resize_click_position = mouse_pos
            self._note_resize_main_note = resize_nc.note()
            usecases.start_notes_resize(self.id)

            return

    def handle_left_mouse_release(self, mouse_pos: Point):
        self.left_mouse_is_pressed = False

        if self.drag_select_active:
            usecases.stop_drag_select(self.id)

        if self.note_resize_active:
            new_size = self._new_note_size_on_resize(mouse_pos)
            usecases.stop_notes_resize(self.id, new_size, self.selected_nc_ids)

        if self.note_drag_active:
            pos_delta = mouse_pos - self.mouse_position_on_left_press
            pos_delta /= self.viewport.height_scale_factor()
            usecases.stop_note_drag(
                self.id, self.selected_nc_ids, pos_delta.to_list())

    def _new_note_size_on_resize(self, new_mouse_pos: Point):
        mouse_delta = new_mouse_pos - self._note_resize_click_position
        size_delta = mouse_delta - self._note_resize_delta_from_note_edge

        size_delta = size_delta / self.viewport.height_scale_factor()
        new_size = self._note_resize_main_note.size() + size_delta

        return new_size

    def _handle_move_on_drag_select(self, mouse_pos: Point):
        selection_rect = Rectangle.from_points(
                self.mouse_position_on_left_press, mouse_pos)

        ncs_in_selection = self.get_note_components_in_area(selection_rect)
        drag_selected_nc_ids = [nc.id for nc in ncs_in_selection]

        usecases.update_drag_select(
            self.id, selection_rect.to_list(), drag_selected_nc_ids)

    def handle_mouse_move(self, mouse_pos: Point):
        delta = self.mouse_position_on_left_press - mouse_pos

        if not self.left_mouse_is_pressed:
            pass
            return

        if self.drag_select_active:
            self._handle_move_on_drag_select(mouse_pos)

        elif self.note_resize_active:
            new_size = self._new_note_size_on_resize(mouse_pos)
            usecases.resize_note_components(
                self.id, new_size.to_list(), self.selected_nc_ids)

        elif self.note_drag_active:
            pos_delta = mouse_pos - self.mouse_position_on_left_press
            pos_delta /= self.viewport.height_scale_factor()
            usecases.note_drag_nc_position_update(
                self.id, self.selected_nc_ids, pos_delta.to_list())

        else:
            # Page viewport change by mouse drag
            unprojected_delta = delta / self.viewport.height_scale_factor()
            new_viewport_center = (self.viewport_position_on_press +
                                   unprojected_delta)

            usecases.change_viewport_center(
                self.id, new_viewport_center.to_list())

    def handle_mouse_scroll(self, steps: int):
        delta = MOVE_SPEED * steps
        current_height = self.viewport.eyeHeight

        new_height = max(MIN_HEIGHT_SCALE,
                         min(current_height - delta, MAX_HEIGHT_SCALE))

        usecases.set_viewport_height(self.id, new_height)

    def handle_left_mouse_double_click(self, mouse_pos: Point):
        nc = self.get_note_component_at(mouse_pos)

        if nc:
            notes_usecases.start_editing_note(
                self.parent_id, nc.id, mouse_pos.to_list())
        else:
            pos = self.viewport.unproject_point(mouse_pos)

            page = misli_gui.entity_for_component(self.id)
            note = Note(page_id=page.id, obj_class='Text', text='')
            note.x = pos.x()
            note.y = pos.y()

            notes_usecases.create_new_note(
                self.parent_id, mouse_pos.to_list(), note.state())
