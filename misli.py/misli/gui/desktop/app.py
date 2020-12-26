from PySide2.QtWidgets import QApplication

from misli import ORGANISATION_NAME, DESKTOP_APP_NAME, DESKTOP_APP_VERSION
from misli.gui.base_component import Component


class DesktopApp(QApplication, Component):
    def __init__(self, parent_id):
        QApplication.__init__(self)
        Component.__init__(self, parent_id=parent_id, obj_class='DesktopApp')

        self.browsers = []

        self.setOrganizationName(ORGANISATION_NAME)
        self.setApplicationName(DESKTOP_APP_NAME)
        self.setApplicationVersion(DESKTOP_APP_VERSION)

        self.browser_window_ids = []
        self.should_quit = False

    def add_child(self, child: Component):
        if child.obj_class == 'BrowserWindow':
            self.browser_window_ids.append(child.id)
            child.showMaximized()

    def remove_child(self, child: Component):
        if child.obj_class == 'BrowserWindow':
            Component.remove_child(self, child)
            child.close()

    def update(self):
        if self.should_quit:
            self.exit()
