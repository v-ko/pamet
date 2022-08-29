from PySide6.QtWidgets import QApplication

import misli
from misli.logging import LoggingLevels, LOGGING_LEVEL
import pamet

log = misli.get_logger(__name__)


class DesktopApp(QApplication):
    def __init__(self):
        QApplication.__init__(self)

        name = 'pamet'

        if LOGGING_LEVEL == LoggingLevels.DEBUG:
            name += '-debug'

        self.setOrganizationName('p10')
        self.setApplicationName(name)
        self.setApplicationVersion(pamet.__version__)
