from dataclasses import dataclass
from PySide2.QtWidgets import QApplication

import misli
from misli import Entity, register_entity
from pamet.constants import ORGANISATION_NAME, DESKTOP_APP_NAME
from pamet.constants import DESKTOP_APP_VERSION

from misli_gui.base_view import View
log = misli.get_logger(__name__)


@register_entity
@dataclass
class DesktopAppViewModel(Entity):
    pass


class DesktopApp(QApplication, View):
    view_class = 'DesktopApp'

    def __init__(self):
        QApplication.__init__(self)
        View.__init__(
            self,
            parent_id='',
            initial_model=DesktopAppViewModel()
        )

        self.browser_windows = {}

        self.setOrganizationName(ORGANISATION_NAME)
        self.setApplicationName(DESKTOP_APP_NAME)
        self.setApplicationVersion(DESKTOP_APP_VERSION)

        self.window_ids = set()

    def handle_child_changes(self, added, removed, updated):
        for child in added:
            self.browser_windows[child.id] = child
            child.showMaximized()

        for child in removed:
            self.browser_windows.pop(child.id)
