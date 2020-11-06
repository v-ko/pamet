from PySide2.QtWidgets import QMainWindow, QPushButton
from PySide2.QtGui import QIcon
from misli.gui.desktop.ui_browser_window import Ui_BrowserWindow

# from misli import misli
from misli.gui.map_page.map_page_qt_component import MapPageQtComponent


class BrowserWindow(QMainWindow):
    def __init__(self):
        super(BrowserWindow, self).__init__()

        self.ui = Ui_BrowserWindow()
        self.ui.setupUi(self)

        self.menuButton = QPushButton(QIcon.fromTheme('menu'), '')
        self.ui.tabWidget.setCornerWidget(self.menuButton)

        self.ui.tabWidget.currentChanged.connect(
            self.handle_tab_changed)

        mock_mpc = MapPageQtComponent('ИИ')
        self.ui.tabWidget.addTab(mock_mpc, 'daimuu')

    def handle_tab_changed(self, index):
        self.ui.tabWidget.widget(0).update()
        print('tab changed')
