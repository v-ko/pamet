from PySide2.QtWidgets import QMainWindow, QPushButton
from PySide2.QtGui import QIcon

from misli.dataclasses import dataclass, Entity

import misli_gui
from misli_gui.base_view import View

from pamet_desktop import usecases

from .ui_browser_window import Ui_BrowserWindow

BROWSER_WINDOW_COMPONENT = 'BrowserWindow'


@dataclass
class BrowserWindowModelView(Entity):
    obj_class: str = BROWSER_WINDOW_COMPONENT
    app_id: str = None
    tab_ids: set = set


class BrowserWindowView(QMainWindow, View):
    def __init__(self, parent_id):
        QMainWindow.__init__(self)
        View.__init__(
            self,
            parent_id=parent_id,
            initial_model=BrowserWindowModelView(),
            obj_class=BROWSER_WINDOW_COMPONENT)

        self._tabs = {}  # By id

        self.ui = Ui_BrowserWindow()
        self.ui.setupUi(self)

        self.menuButton = QPushButton(QIcon.fromTheme('menu'), '')
        self.ui.tabWidget.setCornerWidget(self.menuButton)
        self.ui.tabWidget.currentChanged.connect(
            self.handle_tab_changed)

    def handle_child_changes(self, added, removed, updated):
        for child in added:
            self.ui.tabWidget.addTab(child, child.last_model.name)

        for child in removed:
            tab_idx = self.ui.tabWidget.indexOf(child)
            self.ui.tabWidget.removeTab(tab_idx)

        for child in updated:
            self.handle_child_updated(child)

    def handle_child_updated(self, child):
        tab_idx = self.ui.tabWidget.indexOf(child)
        self.ui.tabWidget.setTabText(tab_idx, child.last_model.name)

    def handle_tab_changed(self, index: int):
        self.ui.tabWidget.widget(0).update()

    def update(self):
        pass

    def closeEvent(self, close_event):
        usecases.close_browser_window(self.id)
