from PySide2.QtWidgets import QApplication

import misli
# from misli import Change
from misli.dataclasses import dataclass, Entity
from misli.constants import ORGANISATION_NAME, DESKTOP_APP_NAME
from misli.constants import DESKTOP_APP_VERSION

import misli_gui
from misli_gui.base_component import Component

# from pamet_desktop.browser_window import BrowserWindow

log = misli.get_logger(__name__)

DESKTOP_APP_COMPONENT = 'DesktopApp'


@dataclass
class DesktopAppComponentState(Entity):
    dummy_prop: bool


class DesktopAppComponent(QApplication, Component):
    def __init__(self):
        QApplication.__init__(self)
        Component.__init__(
            self,
            parent_id='',
            default_state=DesktopAppComponentState(),
            obj_class=DESKTOP_APP_COMPONENT)

        # self.component = DesktopAppComponent()
        # misli_gui.add_component(self.component)

        # misli.subscribe_to_entity(
        #     misli_gui.COMPONENTS_CHANNEL,
        #     self.component.id,
        #     self.handle_component_change)

        self.browser_windows = {}

        self.setOrganizationName(ORGANISATION_NAME)
        self.setApplicationName(DESKTOP_APP_NAME)
        self.setApplicationVersion(DESKTOP_APP_VERSION)

        self.window_ids = set()

    # @log.traced
    # def handle_state_update(self, message: dict):
    #     change = Change(**message)
    #     if change.is_update():
    #         component = DesktopAppComponent(**change.last_state())

    #         if component.window_ids != self.window_ids:
    #             opened_windows_ids = component.window_ids - self.window_ids
    #             closed_windows_ids = self.window_ids - component.window_ids

    #             for ow_id in opened_windows_ids:
    #                 self.open_window(ow_id)

    #             for cw_id in closed_windows_ids:
    #                 self.close_window(cw_id)

    #     if change.is_delete():
    #         self.exit()

    # @log.traced
    # def handle_state_update(self, old_state, new_state):

    #         if component.window_ids != self.window_ids:
    #             opened_windows_ids = component.window_ids - self.window_ids
    #             closed_windows_ids = self.window_ids - component.window_ids

    #             for ow_id in opened_windows_ids:
    #                 self.open_window(ow_id)

    #             for cw_id in closed_windows_ids:
    #                 self.close_window(cw_id)

        # if change.is_delete():
        #     self.exit()

    def handle_child_changes(self, added, removed, updated):
        for child in added:
            self.handle_child_added(child)

        for child in removed:
            self.handle_child_removed(child)

    def handle_child_added(self, child):
        # self.browser_windows[window_id] = child
        child.showMaximized()

    def handle_child_removed(self, child):
        # window = self.browser_windows[window_id]
        child.close()
        # del self.browser_windows[window_id]

    # def open_window(self, window_id):
    #     component = misli_gui.component(window_id)
    #     window = BrowserWindow(component)
    #     window.showMaximized()
    #     self.browser_windows[window_id] = window

    # def close_window(self, window_id):
    #     window = self.browser_windows[window_id]
    #     window.close()
    #     # del self.browser_windows[window_id]

    # def add_child(self, child: Component):
    #     if child.obj_class == 'BrowserWindow':
    #         self.browser_window_ids.append(child.id)
    #         child.showMaximized()

    # def remove_child(self, child: Component):
    #     if child.obj_class == 'BrowserWindow':
    #         Component.remove_child(self, child)
    #         child.close()

    # def update(self):
    #     self.exit()


misli_gui.components_lib.add(DESKTOP_APP_COMPONENT, DesktopAppComponent)
