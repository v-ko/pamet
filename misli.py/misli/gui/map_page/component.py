from misli.gui.component import Component
from misli.gui.map_page.viewport import Viewport

from misli import misli, logging
from misli.gui.map_page import usecases
from misli.core.primitives import Point
from misli.gui.constants import MOVE_SPEED, MIN_HEIGHT_SCALE, MAX_HEIGHT_SCALE
log = logging.getLogger(__name__)


class MapPageComponent(Component):
    def __init__(self, page_id):
        super(MapPageComponent, self).__init__(page_id)

        self.viewport = Viewport(self)
        self.left_mouse_is_pressed = False
        self.mouse_position_on_left_press = Point(0, 0)
        self.selected_nc_ids = set()

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
        self.left_mouse_is_pressed = True
        self.viewport_position_on_press = self.viewport.center()

        # if ctrl and shift

        # elif ctrl

        # elif shift

        # else
        usecases.clear_note_selection(self.id)

        nc_under_mouse = self.get_note_component_at(position)
        if nc_under_mouse:
            usecases.update_note_selections(self.id, {nc_under_mouse.id: True})

    def handle_left_mouse_release(self, position):
        self.left_mouse_is_pressed = False

    def handle_mouse_move(self, new_position):
        if self.left_mouse_is_pressed:
            # Page viewport change by mouse drag
            delta = self.mouse_position_on_left_press - new_position
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
