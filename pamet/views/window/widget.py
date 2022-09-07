from PySide6.QtCore import Qt

from PySide6.QtWidgets import QMainWindow, QPushButton, QTabBar, QWidget
from PySide6.QtGui import QIcon, QKeySequence, QMouseEvent, QResizeEvent, QShortcut

from fusion.libs.entity.change import Change
from fusion.platform.qt_widgets import bind_and_apply_state
from fusion.view import View
from pamet import commands
from pamet.views.tab.widget import TabWidget
from pamet.views.command_palette.widget import CommandPaletteViewState
from pamet.views.command_palette.widget import CommandPaletteWidget
from pamet.views.window.corner_widget.widget import CornerWidget
from pamet.views.window.ui_widget import Ui_BrowserWindow
from pamet.actions import window as window_actions
from pamet.actions import tab as tab_actions

WINDOW_MIN_WIDTH = 400
WINDOW_MIN_HEIGHT = 400
COMMAND_VIEW_SIDE_SPACING = 50
COMMAND_VIEW_MIN_WIDTH = WINDOW_MIN_WIDTH - 2 * COMMAND_VIEW_SIDE_SPACING
COMMAND_VIEW_MAX_WIDTH = 600


class TabBar(QTabBar):  # Adds a tab close on middle-click

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MiddleButton:
            self.tabCloseRequested.emit(self.tabAt(event.pos()))
        return super().mouseReleaseEvent(event)


class WindowWidget(QMainWindow, View):

    def __init__(self, initial_state):
        QMainWindow.__init__(self)
        View.__init__(self, initial_state)

        self.ui = Ui_BrowserWindow()
        self.ui.setupUi(self)
        self.setMinimumWidth(WINDOW_MIN_WIDTH)
        self.setMinimumHeight(WINDOW_MIN_HEIGHT)

        self.tab_widgets = {}
        self.command_widget: QWidget = None

        self.menuButton = QPushButton(QIcon.fromTheme('menu'), '')
        self.corner_widget = CornerWidget(self)

        self.ui.tabBarWidget.setTabBar(TabBar())
        self.ui.tabBarWidget.setTabsClosable(True)
        self.ui.tabBarWidget.setCornerWidget(self.corner_widget)

        self.ui.tabBarWidget.currentChanged.connect(self.handle_tab_changed)
        self.ui.tabBarWidget.tabCloseRequested.connect(
            self.handle_tab_close_requested)

        QShortcut(QKeySequence('ctrl+shift+P'), self,
                  commands.open_command_palette)
        QShortcut(QKeySequence('ctrl+shift+F'), self,
                  commands.show_global_search)
        QShortcut(QKeySequence(Qt.Key_Escape), self, self.handle_esc_shorcut)
        QShortcut(QKeySequence('ctrl+w'), self, commands.close_current_tab)

        go_to_file_shortcut = QShortcut(QKeySequence('ctrl+P'), self)
        go_to_file_shortcut.activated.connect(
            commands.open_command_palette_go_to_file)

        bind_and_apply_state(self, initial_state, self.on_state_change)

    def on_state_change(self, change: Change):
        if change.updated.title:
            self.setWindowTitle(change.last_state().title)

        for tab_state in change.added.tab_states:
            tab = TabWidget(parent=self, initial_state=tab_state)
            self.ui.tabBarWidget.addTab(tab, tab_state.title)
            self.tab_widgets[tab_state.view_id] = tab

        for tab_state in change.removed.tab_states:
            tab = self.tab_widgets[tab_state.view_id]
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
            self.close()
            return

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

    def handle_esc_shorcut(self):
        # We're handling the escape shortcut actions here, since the shortcut
        # context management in Qt doesn't allow overloading (or there's a bug)

        state = self.state()
        # Close the command palette if open
        if state.command_view_state:
            window_actions.close_command_view(state)

        # Propagate to the map page if there's one
        current_tab = self.current_tab()
        if not current_tab:
            return

        tab_state = current_tab.state()
        # Close sidebars if open
        if tab_state.right_sidebar_is_open():
            tab_actions.close_page_properties(tab_state)
        if tab_state.left_sidebar_is_open():
            tab_actions.close_left_sidebar(tab_state)

        map_page = current_tab.page_view()
        if not map_page:
            return

        map_page.handle_esc_shortcut()

    def handle_tab_close_requested(self, tab_index: int):
        tab_widget = self.ui.tabBarWidget.widget(tab_index)
        window_actions.close_tab(self.state(), tab_widget.state())
