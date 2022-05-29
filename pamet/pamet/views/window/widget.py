from dataclasses import field
from PySide6.QtCore import QSize, Qt

from PySide6.QtWidgets import QMainWindow, QPushButton, QWidget
from PySide6.QtGui import QIcon, QKeySequence, QResizeEvent, QShortcut

from misli.entity_library.change import Change
from misli.gui.utils.qt_widgets.qtview import QtView
from misli.gui.view_library.view import View
from misli.gui.views.context_menu.widget import ContextMenuWidget
from pamet import commands
from pamet.views.tab.widget import TabWidget
from pamet.views.command_palette.widget import CommandPaletteViewState
from pamet.views.command_palette.widget import CommandPaletteWidget
from pamet.views.window.ui_widget import Ui_BrowserWindow

from misli.gui import ViewState, view_state_type

WINDOW_MIN_WIDTH = 400
WINDOW_MIN_HEIGHT = 400
COMMAND_VIEW_SIDE_SPACING = 50
COMMAND_VIEW_MIN_WIDTH = WINDOW_MIN_WIDTH - 2 * COMMAND_VIEW_SIDE_SPACING
COMMAND_VIEW_MAX_WIDTH = 600


@view_state_type
class WindowViewState(ViewState):
    title: str = ''
    current_tab_id: str = ''
    tab_states: list = field(default_factory=list)
    command_view_state: View = None

    def __repr__(self) -> str:
        return (f'<WindowViewState title={self.title} {self.current_tab_id=}'
                f' {len(self.tab_states)=}>')


class WindowWidget(QMainWindow, View):

    def __init__(self, initial_state):
        QMainWindow.__init__(self)
        QtView.__init__(
            self,
            initial_state=initial_state,
            on_state_change=self.on_state_change,
        )

        self.ui = Ui_BrowserWindow()
        self.ui.setupUi(self)
        self.setMinimumWidth(WINDOW_MIN_WIDTH)
        self.setMinimumHeight(WINDOW_MIN_HEIGHT)

        self.tab_widgets = {}
        self.command_widget: QWidget = None

        self.menuButton = QPushButton(QIcon.fromTheme('menu'), '')
        self.ui.tabBarWidget.setCornerWidget(self.menuButton)

        self.menuButton.clicked.connect(self.open_main_menu)
        self.ui.tabBarWidget.currentChanged.connect(self.handle_tab_changed)

        open_command_palette_shortcut = QShortcut(QKeySequence('ctrl+shift+P'),
                                                  self)
        open_command_palette_shortcut.activated.connect(
            commands.open_command_palette)

        go_to_file_shortcut = QShortcut(QKeySequence('ctrl+P'), self)
        go_to_file_shortcut.activated.connect(
            commands.open_command_palette_go_to_file)

    def open_main_menu(self):
        entries = {'Page properties': commands.open_page_properties}
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
            tab.deleteLater()

        if change.updated.command_view_state:
            if self.command_widget:
                self.command_widget.deleteLater()
                self.command_widget = None

            command_view_state = change.last_state().command_view_state
            if isinstance(command_view_state, CommandPaletteViewState):
                self.command_widget = CommandPaletteWidget(
                    parent=self, initial_state=command_view_state)
                self.command_widget.show()
                self._update_command_widget_geometry()

    def handle_tab_changed(self, index: int):
        # If there's no tab currently
        if index == -1:
            raise Exception('No tab')  # TODO: handle with opening a new one?

        self.ui.tabBarWidget.widget(index).update()

    def current_tab(self) -> TabWidget:
        return self.ui.tabBarWidget.currentWidget()

    def _update_command_widget_geometry(self):
        if not self.command_widget:
            return

        # Fixed width
        width = self.geometry().size().width()
        command_palette_width = width - 2 * COMMAND_VIEW_SIDE_SPACING
        command_palette_width = min(COMMAND_VIEW_MAX_WIDTH,
                                    command_palette_width)
        command_palette_width = max(COMMAND_VIEW_MIN_WIDTH,
                                    command_palette_width)

        # Max height 40% от self
        command_palette_height = 0.4 * self.geometry().size().height()
        cw_rect = self.command_widget.geometry()

        # Set the size and position centered in the top of the window
        cw_size = cw_rect.size()
        cw_size.setWidth(command_palette_width)
        cw_size.setHeight(command_palette_height)
        cw_rect.setSize(cw_size)

        cw_rect.moveCenter(self.geometry().center())
        cw_rect.moveLeft(width / 2 - command_palette_width / 2)
        cw_rect.moveTop(0)
        self.command_widget.setGeometry(cw_rect)
        self.command_widget.setMaximumHeight(command_palette_height)
        self.command_widget.setMaximumWidth(command_palette_width)
        self.command_widget.setMinimumWidth(command_palette_width)

    def resizeEvent(self, event: QResizeEvent) -> None:
        self._update_command_widget_geometry()
        # return super().resizeEvent(event)
