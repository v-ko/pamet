from PySide6.QtWidgets import QWidget
from fusion.platform.qt_widgets.views.context_menu.widget import ContextMenuWidget
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
        entries = {
            'Page properties': commands.open_page_properties,
            'Open user settings (JSON)': commands.open_user_settings_json,
            'Open repo settings (JSON)': commands.open_repo_settings_json,
            'Export as HTML page /*buggy*': commands.export_as_web_page,
        }
        context_menu = ContextMenuWidget(self, entries=entries)
        context_menu.popup(self.ui.menuButton.rect().bottomRight())
