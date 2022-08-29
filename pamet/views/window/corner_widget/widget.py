from PySide6.QtWidgets import QWidget
from fusion.gui.views.context_menu.widget import ContextMenuWidget
from pamet import commands

from pamet.actions import tab as tab_actions

from .ui_widget import Ui_CornerWidget


class CornerWidget(QWidget):

    def __init__(self, parent):
        super().__init__(parent)

        self.window = parent
        self.ui = Ui_CornerWidget()
        self.ui.setupUi(self)

        self.ui.navigationBackButton.clicked.connect(
            lambda: tab_actions.navigation_back(self.window.current_tab().
                                                state()))

        self.ui.navigationForwardButton.clicked.connect(
            lambda: tab_actions.navigation_forward(self.window.current_tab().
                                                   state()))

        self.ui.navigationToggleButton.clicked.connect(
            lambda: tab_actions.navigation_toggle_last(self.window.current_tab(
            ).state()))

        self.ui.menuButton.clicked.connect(self.open_main_menu)

    def open_main_menu(self):
        entries = {'Page properties': commands.open_page_properties}
        context_menu = ContextMenuWidget(self, entries=entries)
        context_menu.popup(self.ui.menuButton.rect().bottomRight())
