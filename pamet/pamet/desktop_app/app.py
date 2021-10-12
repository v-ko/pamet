from PySide6.QtWidgets import QApplication

import misli
from pamet.constants import ORGANISATION_NAME, DESKTOP_APP_NAME
from pamet.constants import DESKTOP_APP_VERSION

log = misli.get_logger(__name__)


class DesktopApp(QApplication):
    def __init__(self):
        QApplication.__init__(self)

        self.setOrganizationName(ORGANISATION_NAME)
        self.setApplicationName(DESKTOP_APP_NAME)
        self.setApplicationVersion(DESKTOP_APP_VERSION)
