from PySide2.QtWidgets import QMainWindow, QPushButton
from PySide2.QtGui import QIcon

from misli import misli
from misli.gui.desktop.ui_browser_window import Ui_BrowserWindow
from misli.gui.component import Component


class BrowserWindow(QMainWindow, Component):
    def __init__(self, parent_id):
        QMainWindow.__init__(self)
        Component.__init__(self, parent_id, obj_class='BrowserWindow')

        self.ui = Ui_BrowserWindow()
        self.ui.setupUi(self)

        self.menuButton = QPushButton(QIcon.fromTheme('menu'), '')
        self.ui.tabWidget.setCornerWidget(self.menuButton)

        self.ui.tabWidget.currentChanged.connect(
            self.handle_tab_changed)

    def handle_tab_changed(self, index):
        self.ui.tabWidget.widget(0).update()
        print('tab changed')

    def add_child(self, child_id):
        child = misli.component(child_id)
        if child.obj_class == 'BrowserTab':
            self.ui.tabWidget.addTab(child, child.current_page_id)

        # if child.obj_class ==

    def update(self):
        pass
