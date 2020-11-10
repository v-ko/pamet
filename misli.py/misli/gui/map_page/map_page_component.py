from misli.gui.component import Component
from misli.gui.map_page.viewport import Viewport

from misli.gui.map_page import usecases
from misli.core.primitives import Point


class MapPageComponent(Component):
    def __init__(self, page_id):
        super(MapPageComponent, self).__init__(page_id)

        self.viewport = Viewport(self)
        self.left_mouse_is_pressed = False
        self.mouse_position_on_left_press = Point(0, 0)

    def handle_left_mouse_press(self, position):
        self.mouse_position_on_left_press = position
        self.left_mouse_is_pressed = True
        self.viewport_position_on_press = self.viewport.center()

    def handle_left_mouse_release(self, position):
        self.left_mouse_is_pressed = False

    def handle_mouse_move(self, new_position):
        if self.left_mouse_is_pressed:
            # Page viewport change by mouse drag
            delta = self.mouse_position_on_left_press - new_position
            unprojected_delta = delta / self.viewport.height_scale_factor()

            new_viewport_center = (self.viewport_position_on_press +
                                   unprojected_delta)
            usecases.mouse_drag_navigation(self, new_viewport_center)
