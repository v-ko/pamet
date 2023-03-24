from PySide6.QtWidgets import QLabel, QWidget
from PySide6.QtCore import Qt

import fusion
from fusion.libs.entity.change import Change
from fusion.platform.qt_widgets import bind_and_apply_state
from fusion.view import View

from pamet import note_view_type_by_state
from pamet.actions import tab as tab_actions
from pamet.views.map_page.properties_widget import MapPagePropertiesWidget

from pamet.views.map_page.widget import MapPageWidget
from pamet.views.search_bar.widget import SearchBarWidget, SearchBarWidgetState
from pamet.views.semantic_search_bar.widget import SemanticSearchBarWidget, SemanticSearchBarWidgetState
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
        self._search_widget = None
        self._semantic_search_widget = None
        self._page_widget_cache = {}  # By page_id

        self.ui.rightSidebarCloseButton.clicked.connect(
            lambda: tab_actions.close_page_properties(self.state()))
        self.ui.leftSidebarCloseButton.clicked.connect(
            lambda: tab_actions.close_left_sidebar(self.state()))

        self.ui.commandLineEdit.hide()
        self.ui.leftSidebarContainer.hide()

        self.page_not_found_label = QLabel('Page missing.', self)

        # The state should be managed by the window
        bind_and_apply_state(self,
                             initial_state,
                             on_state_change=self.on_state_change)

    def page_view(self) -> MapPageViewState:
        return self._page_view

    def set_search_pane_state(self, pane_state: bool):
        if pane_state:
            if type(pane_state) == SearchBarWidgetState:
                if not self._search_widget:
                    self._search_widget = SearchBarWidget(
                        self, initial_state=pane_state)

                self._left_sidebar_widget = self._search_widget
                self.ui.leftSidebarContainer.layout().addWidget(
                    self._search_widget)

            elif type(pane_state) == SemanticSearchBarWidgetState:
                if not self._semantic_search_widget:
                    self._semantic_search_widget = SemanticSearchBarWidget(
                        self, initial_state=pane_state)

                self._left_sidebar_widget = self._semantic_search_widget
                self.ui.leftSidebarContainer.layout().addWidget(
                    self._semantic_search_widget)

            self.ui.leftSidebarContainer.show()
            self.ui.leftSidebarContainer.raise_()
        else:
            self.ui.leftSidebarContainer.hide()

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
            # Clear the sidebar
            if self._left_sidebar_widget:
                self.ui.leftSidebarContainer.layout().removeWidget(
                    self._left_sidebar_widget)

                # If it's the search bar - don't delete it, we'll reuse it
                if self._left_sidebar_widget not in [
                        self._search_widget, self._semantic_search_widget
                ]:
                    self._left_sidebar_widget.deleteLater()

                self._left_sidebar_widget = None

            self.set_search_pane_state(state.left_sidebar_state)

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

    def remove_page_widget_from_cache(self, page_view_id: str):
        self._page_widget_cache.pop(page_view_id, None)

    def switch_to_page_view(self, page_view_state: MapPageViewState):
        """Switches to the specified page view state.

        The TabWidget keeps a cache with page widgets associated with their
        state ids. When possible - those get reused.
        """
        if self._page_view:
            self.ui.centralContainer.layout().removeWidget(self._page_view)
            if isinstance(self._page_view, MapPageWidget):
                self.add_page_wideget_to_cache(self._page_view)

            self._page_view.hide()

        if not page_view_state:
            page_widget = self.page_not_found_label
        else:
            page_widget = self.cached_page_widget(page_view_state.view_id)
            if not page_widget:
                page_widget = MapPageWidget(parent=self,
                                            initial_state=page_view_state)
        self._page_view = page_widget

        self.ui.centralContainer.layout().addWidget(self._page_view)
        self._page_view.show()

        # Must be visible to accept focus, so queue on the main loop
        fusion.call_delayed(self._page_view.setFocus)

    def clear_page_view(self):
        if not self._page_view:
            return

        self.ui.centralContainer.layout().removeWidget(self._page_view)
        # self._page_view.deleteLater()
        self._page_view = None
