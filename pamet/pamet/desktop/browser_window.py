from dataclasses import dataclass, field
from PySide6.QtWidgets import QMainWindow, QPushButton
from PySide6.QtGui import QIcon

from misli.gui import ViewState, wrap_and_register_view_state_type
from misli.gui import View, register_view_type
from pamet.desktop import usecases

from .ui_browser_window import Ui_BrowserWindow


@wrap_and_register_view_state_type
class BrowserWindowViewState(ViewState):
    name: str = ''
    app_id: str = None
    tab_ids: set = field(default_factory=set)


@register_view_type
class BrowserWindowView(QMainWindow, View):
    def __init__(self, parent_id):
        QMainWindow.__init__(self)
        View.__init__(
            self,
            parent_id=parent_id,
            initial_state=BrowserWindowViewState()
        )

        self._tabs = {}  # By id

        self.ui = Ui_BrowserWindow()
        self.ui.setupUi(self)

        self.menuButton = QPushButton(QIcon.fromTheme('menu'), '')
        self.ui.tabWidget.setCornerWidget(self.menuButton)
        self.ui.tabWidget.currentChanged.connect(
            self.handle_tab_changed)

        self.showMaximized()

    def handle_child_changes(self, added, removed, updated):
        for child in added:
            self.ui.tabWidget.addTab(child, child.state.name)

        for child in removed:
            tab_idx = self.ui.tabWidget.indexOf(child)
            self.ui.tabWidget.removeTab(tab_idx)

        for child in updated:
            tab_idx = self.ui.tabWidget.indexOf(child)
            self.ui.tabWidget.setTabText(tab_idx, child.state.name)

    def handle_tab_changed(self, index: int):
        self.ui.tabWidget.widget(index).update()

    def update(self):
        pass

    def closeEvent(self, close_event):
        usecases.close_browser_window(self.id)
