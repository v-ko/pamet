from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt

import fusion
from fusion.util.point2d import Point2D
from fusion.libs.entity.change import Change
from fusion.platform.qt_widgets import bind_and_apply_state
from fusion.view import View

from pamet import actions, note_view_type_by_state
from pamet.actions import tab as tab_actions
from pamet.model.text_note import TextNote
from pamet.views.map_page.properties_widget import MapPagePropertiesWidget

from pamet.views.map_page.widget import MapPageWidget
from pamet.views.search_bar.widget import SearchBarWidget
from pamet.views.tab.ui_widget import Ui_TabMainWidget

from pamet.views.map_page.state import MapPageViewState

SIDEBAR_WIDTH = 300
MIN_TAB_WIDTH = SIDEBAR_WIDTH * 1.1
MAX_PAGE_CACHE_SIZE = 100


class TabWidget(QWidget, View):

    def __init__(self, parent, initial_state):
        QWidget.__init__(self, parent=parent)
        View.__init__(self, initial_state=initial_state)

        # That's because of a Qt bug - when opening a new tab - the central
        # widget of the tab has a QStackWidget as parent which does not have
        # the window as a parent
        self.parent_window = parent

        self.ui = Ui_TabMainWidget()
        self.ui.setupUi(self)

        self._page_view = None
        self._page_subscription_id = None
        self.edit_view = None
        self._left_sidebar_widget = None
        self._right_sidebar_widget = None
        self._search_bar_widget = None
        self._page_widget_cache = {}  # By page_id

        new_note_shortcut = QShortcut(QKeySequence('N'), self)
        new_note_shortcut.activated.connect(self.create_new_note_command)

        new_page_shortcut = QShortcut(QKeySequence('ctrl+N'), self)
        new_page_shortcut.activated.connect(self.create_new_page_command)

        self.ui.rightSidebarCloseButton.clicked.connect(
            lambda: tab_actions.close_page_properties(self.state()))
        self.ui.leftSidebarCloseButton.clicked.connect(
            lambda: tab_actions.close_left_sidebar(self.state()))

        self.ui.commandLineEdit.hide()
        self.ui.leftSidebarContainer.hide()

        # The state should be managed by the window
        bind_and_apply_state(self,
                                        initial_state,
                                        on_state_change=self.on_state_change)

    def page_view(self) -> MapPageViewState:
        return self._page_view

    def on_state_change(self, change: Change):
        state = change.last_state()
        if change.updated.page_view_state or not self.page_view():
            self.switch_to_page_view(state.page_view_state)

        if change.updated.title:
            self_idx = self.parent_window.ui.tabBarWidget.indexOf(self)
            self.parent_window.ui.tabBarWidget.setTabText(
                self_idx, state.title)

        if change.updated.page_edit_view_state:
            if self._right_sidebar_widget:
                self.ui.rightSidebarContainer.layout().removeWidget(
                    self._right_sidebar_widget)
                self._right_sidebar_widget.deleteLater()
                self._right_sidebar_widget = None

            if state.page_edit_view_state:
                new_widget = MapPagePropertiesWidget(
                    self, initial_state=state.page_edit_view_state)
                self._right_sidebar_widget = new_widget
                self.ui.rightSidebarContainer.layout().addWidget(new_widget)
                self.ui.rightSidebarContainer.show()
                self.ui.rightSidebarContainer.raise_()
            else:
                self.ui.rightSidebarContainer.hide()

        if change.updated.left_sidebar_state:
            if self._left_sidebar_widget:
                self.ui.leftSidebarContainer.layout().removeWidget(
                    self._left_sidebar_widget)

                # If it's the search bar - don't delete it, we'll reuse it
                if self._left_sidebar_widget != self._search_bar_widget:
                    self._left_sidebar_widget.deleteLater()

                self._left_sidebar_widget = None

            if state.left_sidebar_state:
                if not self._search_bar_widget:
                    self._search_bar_widget = SearchBarWidget(
                        self, initial_state=state.left_sidebar_state)
                self._left_sidebar_widget = self._search_bar_widget
                self.ui.leftSidebarContainer.layout().addWidget(
                    self._search_bar_widget)
                self.ui.leftSidebarContainer.show()
                self.ui.leftSidebarContainer.raise_()
            else:
                self.ui.leftSidebarContainer.hide()

        if change.updated.note_edit_view_state:
            if self.edit_view:
                self.edit_view.close()
                self.edit_view.deleteLater()
                self.edit_view = None

            if state.note_edit_view_state:
                EditViewType = note_view_type_by_state(
                    type(state.note_edit_view_state).__name__)
                self.edit_view = EditViewType(
                    parent=self, initial_state=state.note_edit_view_state)
                self.edit_view.setParent(self)
                self.edit_view.setWindowFlag(Qt.Sheet, True)
                self.edit_view.show()
                self.edit_view.setFocus()

    def add_page_wideget_to_cache(self, page_widget: MapPageWidget):
        self._page_widget_cache[page_widget.state().view_id] = page_widget
        if MAX_PAGE_CACHE_SIZE < len(self._page_widget_cache):
            page_id, page_widget = self._page_widget_cache.popitem()
            page_widget.deleteLater()

    def cached_page_widget(self, page_view_id: str):
        return self._page_widget_cache.pop(page_view_id, None)

    def switch_to_page_view(self, page_view_state: MapPageViewState):
        """Switches to the specified page view state.

        The TabWidget keeps a cache with page widgets associated with their
        state ids. When possible - those get reused.
        """
        if self._page_view:
            self.ui.centralContainer.layout().removeWidget(self._page_view)

            self.add_page_wideget_to_cache(self._page_view)
            self._page_view.hide()

        if not page_view_state:
            return

        page_widget = self.cached_page_widget(page_view_state.view_id)
        if not page_widget:
            page_widget = MapPageWidget(parent=self,
                                        initial_state=page_view_state)

        self._page_view = page_widget
        self.ui.centralContainer.layout().addWidget(page_widget)
        self._page_view.show()

        # Must be visible to accept focus, so queue on the main loop
        fusion.call_delayed(page_widget.setFocus)

    def create_new_note_command(self):
        page_widget = self.page_view()

        # If the mouse is on the page - make the note on its position.
        # Else: make it in the center of the viewport
        if page_widget.underMouse():
            edit_window_pos = self.cursor().pos()
        else:
            edit_window_pos = page_widget.geometry().center()

        edit_window_pos = Point2D(edit_window_pos.x(), edit_window_pos.y())
        note_pos = page_widget.state().unproject_point(edit_window_pos)
        new_note = TextNote()
        new_note = new_note.with_id(page_id=page_widget.state().page_id)
        new_note.x = note_pos.x()
        new_note.y = note_pos.y()
        actions.note.create_new_note(self.state(), new_note)

    def create_new_page_command(self):
        mouse_pos = self.cursor().pos()
        edit_window_pos = Point2D(mouse_pos.x(), mouse_pos.y())
        tab_actions.create_new_page(self.state(), edit_window_pos)
