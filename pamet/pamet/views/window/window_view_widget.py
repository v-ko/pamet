from PySide6.QtWidgets import QMainWindow, QPushButton
from PySide6.QtGui import QIcon

from misli.gui import register_view_type
from pamet.actions import desktop
from pamet.views.window.ui_window_view_widget import Ui_BrowserWindow
from pamet.views.window.view import BrowserWindowView


@register_view_type
class BrowserWindowViewWidget(QMainWindow, BrowserWindowView):
    def __init__(self, parent_id):
        QMainWindow.__init__(self)
        BrowserWindowView.__init__(self, parent_id)

        self.ui = Ui_BrowserWindow()
        self.ui.setupUi(self)

        self.menuButton = QPushButton(QIcon.fromTheme('menu'), '')
        self.ui.tabWidget.setCornerWidget(self.menuButton)
        self.ui.tabWidget.currentChanged.connect(self.handle_tab_changed)

        self.showMaximized()

    def on_child_added(self, child):
        self.ui.tabWidget.addTab(child, child.state.name)

    def on_child_updated(self, child):
        tab_idx = self.ui.tabWidget.indexOf(child)
        self.ui.tabWidget.setTabText(tab_idx, child.state.name)

    def on_child_removed(self, child):
        tab_idx = self.ui.tabWidget.indexOf(child)
        self.ui.tabWidget.removeTab(tab_idx)

    def handle_tab_changed(self, index: int):
        self.ui.tabWidget.widget(index).update()

    def update(self):
        pass

    def closeEvent(self, close_event):
        desktop.close_browser_window(self.id)
