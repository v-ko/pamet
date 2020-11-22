from PySide2.QtWidgets import QApplication

from misli import misli
from misli import ORGANISATION_NAME, DESKTOP_APP_NAME, DESKTOP_APP_VERSION
from misli.gui.component import Component


class DesktopApp(QApplication, Component):  # rename to QtApp ?
    def __init__(self):
        QApplication.__init__(self)
        Component.__init__(self, parent_id='', obj_class='DesktopApp')

        self.id = '__desktop_app__'
        self._misli = misli
        self.browsers = []

        self.setOrganizationName(ORGANISATION_NAME)
        self.setApplicationName(DESKTOP_APP_NAME)
        self.setApplicationVersion(DESKTOP_APP_VERSION)

        self.browser_window_ids = []

    def add_child(self, child_id):
        child = misli.component(child_id)
        if child.obj_class == 'BrowserWindow':
            self.browser_window_ids.append(child.id)
            child.showMaximized()

    def update(self):
        pass
