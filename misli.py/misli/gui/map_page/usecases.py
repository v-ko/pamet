from misli import misli
# def handle_mouse_left_press(map_page_component, position):
#     #     self.mousePosOnPress = event.pos()
#     # self.viewportPosOnPress = self.viewport.center
#     # self.canvasDrag.start()
#     pass


# def handle_mouse_left_release(map_page_component, position):
#     # if self.canvasDrag.isActive():
#     #             self.canvasDrag.stop()
#     pass
#
def mouse_drag_navigation(map_page_component, new_viewport_center):
    map_page_component.viewport.set_center(new_viewport_center)
    misli.update_component(map_page_component.id)
