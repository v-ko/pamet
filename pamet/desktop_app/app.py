from PySide6.QtWidgets import QApplication

import fusion
from fusion.logging import LoggingLevels, LOGGING_LEVEL
import pamet

log = fusion.get_logger(__name__)


class DesktopApp(QApplication):
    def __init__(self):
        QApplication.__init__(self)

        name = 'pamet'

        if LOGGING_LEVEL == LoggingLevels.DEBUG:
            name += '-debug'

        self.setOrganizationName('p10')
        self.setApplicationName(name)
        self.setApplicationVersion(pamet.__version__)
        self.setQuitOnLastWindowClosed(True)  # Needed for some reason
