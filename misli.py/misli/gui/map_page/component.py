import time

from misli.gui.component import Component
from misli.gui.map_page.viewport import Viewport

from misli import misli, logging
from misli.gui.desktop.helpers import control_is_pressed, shift_is_pressed
from misli.gui.map_page import usecases
from misli.core.primitives import Point, Rectangle
from misli.gui.constants import MOVE_SPEED, MIN_HEIGHT_SCALE, MAX_HEIGHT_SCALE
from misli.gui.notes import usecases as notes_usecases
log = logging.getLogger(__name__)


class MapPageComponent(Component):
    def __init__(self, parent_id):
        Component.__init__(self, parent_id, obj_class='MapPage')

        self.viewport = Viewport(self)
        self.left_mouse_is_pressed = False
        self.mouse_position_on_left_press = Point(0, 0)
        self.selected_nc_ids = set()
        self.left_mouse_last_press_time = 0

        class DragSelect():
            def __init__(self):
                self.nc_ids = []
                self.active = False
                self.rect = None

        self.drag_select = DragSelect()

    def get_note_components_in_area(self, rect):
        unprojected_rect = self.viewport.unproject_rect(rect)
        intersecting = []

        for child in self.get_children():
            note = misli.base_object_for_component(child.id)

            if note.rect().intersects(unprojected_rect):
                intersecting.append(child)

        return intersecting

    def get_note_components_at(self, position):
        unprojected_mouse_pos = self.viewport.unproject_point(position)
        intersecting = []

        for child in self.get_children():
            note = misli.base_object_for_component(child.id)

            if note.rect().contains(unprojected_mouse_pos):
                intersecting.append(child)

        return intersecting

    def get_note_component_at(self, position):
        intersecting = self.get_note_components_at(position)
        if not intersecting:
            return None

        return intersecting[0]

    def handle_left_mouse_press(self, position):
        self.mouse_position_on_left_press = position
        self.left_mouse_last_press_time = time.time()
        self.left_mouse_is_pressed = True
        self.viewport_position_on_press = self.viewport.center()

        ctrl_pressed = control_is_pressed()
        shift_pressed = shift_is_pressed()

        nc_under_mouse = self.get_note_component_at(position)

        if ctrl_pressed and shift_pressed:
            usecases.update_drag_select(self.id, True)

        elif ctrl_pressed:
            if nc_under_mouse:
                nc_selected = nc_under_mouse.id in self.selected_nc_ids
                usecases.update_note_selections(
                    self.id, {nc_under_mouse.id: not nc_selected})

        else:
            usecases.clear_note_selection(self.id)
            if nc_under_mouse:
                usecases.update_note_selections(
                    self.id, {nc_under_mouse.id: True})

    def handle_left_mouse_release(self, position):
        self.left_mouse_is_pressed = False
        usecases.update_drag_select(self.id, False)

    def handle_mouse_move(self, new_position):
        delta = self.mouse_position_on_left_press - new_position

        if self.drag_select.active:
            selection_rect = Rectangle. from_points(
                self.mouse_position_on_left_press, new_position)
            ncs_in_selection = self.get_note_components_in_area(selection_rect)
            drag_selected_nc_ids = [nc.id for nc in ncs_in_selection]

            self.drag_select.rect = selection_rect
            usecases.update_drag_select(self.id, True, drag_selected_nc_ids)

            return

        if self.left_mouse_is_pressed:
            # Page viewport change by mouse drag
            unprojected_delta = delta / self.viewport.height_scale_factor()
            new_viewport_center = (self.viewport_position_on_press +
                                   unprojected_delta)

            usecases.mouse_drag_navigation(self.id, new_viewport_center)

    def handle_mouse_scroll(self, steps):
        delta = MOVE_SPEED * steps
        current_height = self.viewport.eyeHeight

        new_height = max(MIN_HEIGHT_SCALE,
                         min(current_height - delta, MAX_HEIGHT_SCALE))

        usecases.set_viewport_height(self.id, new_height)

    def handle_left_mouse_double_click(self, position):
        nc = self.get_note_component_at(position)

        if nc:
            notes_usecases.start_editing_note(self.parent_id, nc.id, position)
        else:
            pass