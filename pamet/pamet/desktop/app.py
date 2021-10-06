from dataclasses import dataclass
from PySide6.QtWidgets import QApplication

import misli
from misli.gui import ViewState, wrap_and_register_view_state_type
from misli.gui.view_library import register_view_type
from misli.gui.view_library.view import View

from pamet.constants import ORGANISATION_NAME, DESKTOP_APP_NAME
from pamet.constants import DESKTOP_APP_VERSION

log = misli.get_logger(__name__)


@wrap_and_register_view_state_type
class DesktopAppViewState(ViewState):
    pass


@register_view_type
class DesktopApp(QApplication, View):
    def __init__(self):
        QApplication.__init__(self)
        View.__init__(
            self,
            parent_id='',
            initial_state=DesktopAppViewState()
        )

        self.browser_windows = {}

        self.setOrganizationName(ORGANISATION_NAME)
        self.setApplicationName(DESKTOP_APP_NAME)
        self.setApplicationVersion(DESKTOP_APP_VERSION)

        self.window_ids = set()

    def handle_child_changes(self, added, removed, updated):
        for child in added:
            self.browser_windows[child.id] = child
            # child.showMaximized()

        for child in removed:
            self.browser_windows.pop(child.id)
