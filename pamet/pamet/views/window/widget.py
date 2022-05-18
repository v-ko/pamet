from dataclasses import field

from PySide6.QtWidgets import QMainWindow, QPushButton
from PySide6.QtGui import QIcon

from misli.entity_library.change import Change
from misli.gui.utils.qt_widgets.qtview import QtView
from misli.gui.view_library.view import View
from misli.gui.views.context_menu.widget import ContextMenuWidget
from pamet import commands
from pamet.views.tab.widget import TabWidget
from pamet.views.window.ui_widget import Ui_BrowserWindow

from misli.gui import ViewState, view_state_type


@view_state_type
class WindowViewState(ViewState):
    title: str = ''
    current_tab_id: str = ''
    tab_states: list = field(default_factory=list)

    def __repr__(self) -> str:
        return (f'<WindowViewState title={self.title} {self.current_tab_id=}'
                f' {len(self.tab_states)=}>')


class WindowWidget(QMainWindow, View):

    def __init__(self, initial_state):
        QMainWindow.__init__(self)
        QtView.__init__(self,
                        initial_state=initial_state,
                        on_state_change=self.on_state_change)

        self.ui = Ui_BrowserWindow()
        self.ui.setupUi(self)

        self.tab_widgets = {}

        self.menuButton = QPushButton(QIcon.fromTheme('menu'), '')
        self.ui.tabBarWidget.setCornerWidget(self.menuButton)

        self.menuButton.clicked.connect(self.open_main_menu)
        self.ui.tabBarWidget.currentChanged.connect(self.handle_tab_changed)

    def open_main_menu(self):
        entries = {
            'Page properties': commands.open_page_properties
        }
        context_menu = ContextMenuWidget(self, entries=entries)
        context_menu.popup_on_mouse_pos()

    def on_state_change(self, change: Change):
        if change.updated.title:
            self.setWindowTitle(change.last_state().title)

        for tab_state in change.added.tab_states:
            tab = TabWidget(parent=self, initial_state=tab_state)
            self.ui.tabBarWidget.addTab(tab, tab_state.title)
            self.tab_widgets[tab_state.id] = tab

        for tab_state in change.removed.tab_states:
            tab = self.tab_widgets[tab_state.id]
            tab_idx = self.ui.tabBarWidget.indexOf(tab)
            self.ui.tabBarWidget.removeTab(tab_idx)

    def handle_tab_changed(self, index: int):
        # If there's no tab currently
        if index == -1:
            raise Exception('No tab')  # TODO: handle with opening a new one?

        self.ui.tabBarWidget.widget(index).update()

    def current_tab(self) -> TabWidget:
        return self.ui.tabBarWidget.currentWidget()
