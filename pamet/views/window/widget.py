import sys
from PySide6.QtCore import Qt

from PySide6.QtWidgets import QMainWindow, QMessageBox, QPushButton, QTabBar, QWidget
from PySide6.QtGui import QIcon, QKeySequence, QMouseEvent, QResizeEvent, QShortcut
from PySide6.QtCore import __version__ as qt_version
import fusion

from fusion.libs.entity.change import Change
from fusion.platform.qt_widgets import bind_and_apply_state
from fusion.view import View
from pamet import commands
import pamet
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

        # Setup main menu
        # Page menu
        self.ui.actionNew_page.triggered.connect(commands.create_new_page)
        self.ui.actionGo_to_page.triggered.connect(
            commands.open_command_palette_go_to_file)
        self.ui.actionRefresh.triggered.connect(commands.refresh_page)
        self.ui.actionPageProperties.triggered.connect(
            commands.open_page_properties)

        # Note menu
        self.ui.actionNew_note.triggered.connect(commands.create_new_note)
        self.ui.actionCreate_arrow.triggered.connect(
            commands.start_arrow_creation)
        self.ui.actionEdit_note.triggered.connect(commands.edit_selected_notes)
        self.ui.actionSelect_all.triggered.connect(commands.select_all)
        self.ui.actionCopy.triggered.connect(commands.copy)
        self.ui.actionPaste.triggered.connect(commands.paste)
        self.ui.actionPaste_special.triggered.connect(commands.paste_special)
        self.ui.actionCut.triggered.connect(commands.cut)
        self.ui.actionDelete_selected.triggered.connect(
            commands.delete_selected)
        self.ui.actionUndo.triggered.connect(commands.undo)
        self.ui.actionRedo.triggered.connect(commands.redo)
        self.ui.actionAutosize.triggered.connect(
            commands.autosize_selected_notes)
        self.ui.actionColorSelectedBlue.triggered.connect(
            commands.color_selected_notes_blue)
        self.ui.actionColorSelectedGreen.triggered.connect(
            commands.color_selected_notes_green)
        self.ui.actionColorSelectedRed.triggered.connect(
            commands.color_selected_notes_red)
        self.ui.actionColorSelectedBlack.triggered.connect(
            commands.color_selected_notes_black)
        self.ui.actionRemove_background.triggered.connect(
            commands.make_background_transparent_for_selected_notes)
        self.ui.actionBlue_shift.triggered.connect(
            commands.blue_shift_selected)
        self.ui.actionGreen_shift.triggered.connect(
            commands.green_shift_selected)
        self.ui.actionRed_shift.triggered.connect(commands.red_shift_selected)
        self.ui.actionBlack_shift.triggered.connect(
            commands.black_shift_selected)
        self.ui.actionTransparency_shift.triggered.connect(
            commands.shift_selected_note_transparency)

        # Other menu
        self.ui.actionGrab_screen_snippet.triggered.connect(
            commands.grab_screen_snippet)
        self.ui.actionGlobal_search.triggered.connect(
            commands.show_global_search)
        self.ui.actionOpen_command_palette.triggered.connect(
            commands.open_command_palette)
        self.ui.actionOpen_user_settings.triggered.connect(
            commands.open_user_settings_json)
        self.ui.actionOpen_repo_settings.triggered.connect(
            commands.open_repo_settings_json)
        # Navigation
        self.ui.actionBack.triggered.connect(commands.navigate_back)
        self.ui.actionForward.triggered.connect(commands.navigate_forward)
        self.ui.actionToggle.triggered.connect(
            commands.toggle_between_last_two_pages)

        def show_about_dialog():
            QMessageBox.about(
                self, 'About Pamet', f"""
            <h1>Pamet</h1>
            <p>An app for organizing notes and thoughts.</p>
            <p> Github:
                <a href="https://github.com/v-ko/pamet">
                    https://github.com/v-ko/pamet
                </a>
            </p>
            <p>Version: {pamet.__version__}</p>
            <p>Fusion version: {fusion.__version__}</p>
            <p>Qt version: {qt_version}</p>
            <p>Python version: {sys.version}</p>
            """)

        def show_help_dialog():
            QMessageBox.about(
                self, 'Help', """
            <h1>Help</h1>
            <h3>Navigation</h3>
            <p>Click and drag to pan around. Scroll to zoom in/out.</p>
            <h3>Selection</h3>
            <p>Right click and drag selects or moves notes.
            Left-click with ctrl+shift does the same.</p>
            <h3>Editing</h3>
            <p>Double click to edit a note or create one.</p>
            <h3>Other</h3>
            <p>Check out the rest of the commands in the command palette
            (ctrl+shift+P) or browse the menus</p>
            """)

        self.ui.actionAbout.triggered.connect(show_about_dialog)
        self.ui.actionHelp.triggered.connect(show_help_dialog)

        self.tab_widgets = {}
        self.command_widget: QWidget = None

        self.menuButton = QPushButton(QIcon.fromTheme('menu'), '')
        self.corner_widget = CornerWidget(self)

        self.ui.tabBarWidget.setTabsClosable(True)
        self.ui.tabBarWidget.setCornerWidget(self.corner_widget)

        self.ui.tabBarWidget.currentChanged.connect(self.handle_tab_changed)
        self.ui.tabBarWidget.tabCloseRequested.connect(
            self.handle_tab_close_requested)

        # QShortcut(QKeySequence('ctrl+shift+P'), self,
        #           commands.open_command_palette)
        # QShortcut(QKeySequence('ctrl+shift+F'), self,
        #           commands.show_global_search)
        QShortcut(QKeySequence(Qt.Key_Escape), self, self.handle_esc_shorcut)
        QShortcut(QKeySequence('ctrl+w'), self, commands.close_current_tab)

        def go_to_tab_num(num):
            self.ui.tabBarWidget.setCurrentIndex(num - 1)

        QShortcut(QKeySequence('ctrl+1'), self, lambda: go_to_tab_num(1))
        QShortcut(QKeySequence('ctrl+2'), self, lambda: go_to_tab_num(2))
        QShortcut(QKeySequence('ctrl+3'), self, lambda: go_to_tab_num(3))
        QShortcut(QKeySequence('ctrl+4'), self, lambda: go_to_tab_num(4))
        QShortcut(QKeySequence('ctrl+5'), self, lambda: go_to_tab_num(5))
        QShortcut(QKeySequence('ctrl+6'), self, lambda: go_to_tab_num(6))
        QShortcut(QKeySequence('ctrl+7'), self, lambda: go_to_tab_num(7))
        QShortcut(QKeySequence('ctrl+8'), self, lambda: go_to_tab_num(8))
        QShortcut(QKeySequence('ctrl+9'), self, lambda: go_to_tab_num(9))

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
