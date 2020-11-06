from PySide2.QtWidgets import QApplication

from misli import misli
from misli import ORGANISATION_NAME, DESKTOP_APP_NAME, DESKTOP_APP_VERSION
from misli.objects import State
from misli.gui.desktop.browser_window import BrowserWindow

default_state = State(obj_type='DesktopApp')


class DesktopApp(QApplication):  # rename to QtApp ?
    def __init__(self):
        super(DesktopApp, self).__init__()

        self._misli = misli
        self.browsers = []

        self.setOrganizationName(ORGANISATION_NAME)
        self.setApplicationName(DESKTOP_APP_NAME)
        self.setApplicationVersion(DESKTOP_APP_VERSION)

        browser = BrowserWindow()
        self.browsers.append(browser)
        browser.showMaximized()
