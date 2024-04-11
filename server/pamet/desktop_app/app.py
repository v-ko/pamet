import traceback
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

import fusion
from fusion.logging import LoggingLevels, LOGGING_LEVEL
import pamet
from pamet.views.selector_widget import SelectorWidget

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

        # TODO: This is a hack to make the app not crash when showing
        # a message box from a command
        self.message_box = QMessageBox()

        # Selector widget for grabbing screen snipptes
        self.selector_widget = SelectorWidget()

    def hacky_present_modal(self, dialog):
        # Otherwise the app crashes when showing the dialog from a command
        def present():
            dialog.exec()

        QTimer.singleShot(0, present)

    def present_exception(self, exception: Exception, title: str = None):
        title = title or 'Exception raised'
        text = str(exception) + '\n\nTraceback:\n' + traceback.format_exc()
        self.message_box.setText(text)
        self.message_box.setWindowTitle(title)
        self.message_box.setIcon(QMessageBox.Critical)
        self.hacky_present_modal(self.message_box)
