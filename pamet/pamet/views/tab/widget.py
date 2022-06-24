from dataclasses import field

from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt

import misli
from misli.basic_classes.point2d import Point2D
from misli.entity_library.change import Change
from misli.gui.utils import qt_widgets
from misli.gui.view_library.view import View
from pamet import actions, note_view_type_by_state
from pamet.actions import tab as tab_actions
from pamet.model.text_note import TextNote
from pamet.views.map_page.properties_widget import MapPagePropertiesWidget

from pamet.views.map_page.widget import MapPageWidget
from pamet.views.tab.ui_widget import Ui_TabMainWidget

from misli.gui import ViewState, view_state_type
from pamet.model import Note
from pamet.views.map_page.state import MapPageViewState

SIDEBAR_WIDTH = 300
MIN_TAB_WIDTH = SIDEBAR_WIDTH * 1.1


@view_state_type
class TabViewState(ViewState):
    title: str = ''
    page_view_state: MapPageViewState = field(default=None)
    edit_view_state: ViewState = None
    creating_note: Note = None
    right_sidebar_state: ViewState = None
    right_sidebar_visible: bool = False
    page_properties_open: bool = False

    def __repr__(self) -> str:
        return (f'<TabViewState title={self.title}>')


# @register_view_type
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
        self._right_sidebar_widget = None

        new_note_shortcut = QShortcut(QKeySequence('N'), self)
        new_note_shortcut.activated.connect(self.create_new_note_command)

        new_page_shortcut = QShortcut(QKeySequence('ctrl+N'), self)
        new_page_shortcut.activated.connect(self.create_new_page_command)

        self.ui.rightSidebarCloseButton.clicked.connect(
            lambda: tab_actions.close_right_sidebar(self.state()))
        # TODO: same for the left

        self.ui.commandLineEdit.hide()
        self.ui.leftSidebarContainer.hide()

        # The state should be managed by the window
        qt_widgets.bind_and_apply_state(self,
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

        if change.updated.right_sidebar_state:
            if self._right_sidebar_widget:
                self.ui.rightSidebarContainer.layout().removeWidget(
                    self._right_sidebar_widget)
                self._right_sidebar_widget.deleteLater()
                self._right_sidebar_widget = None

            if state.right_sidebar_state:
                new_widget = MapPagePropertiesWidget(
                    self, initial_state=state.right_sidebar_state)
                self._right_sidebar_widget = new_widget
                self.ui.rightSidebarContainer.layout().addWidget(new_widget)

        if change.updated.right_sidebar_visible:
            if state.right_sidebar_visible:
                self.ui.rightSidebarContainer.show()
                self.ui.rightSidebarContainer.raise_()
            else:
                self.ui.rightSidebarContainer.hide()

        if change.updated.edit_view_state:
            if self.edit_view:
                self.edit_view.close()
                self.edit_view.deleteLater()
                self.edit_view = None

            if state.edit_view_state:
                EditViewType = note_view_type_by_state(
                    type(state.edit_view_state).__name__)
                self.edit_view = EditViewType(
                    parent=self, initial_state=state.edit_view_state)
                self.edit_view.setParent(self)
                self.edit_view.setWindowFlag(Qt.Sheet, True)
                self.edit_view.show()
                self.edit_view.setFocus()

    def switch_to_page_view(self, page_view_state):
        if self._page_view:
            self.ui.centralContainer.layout().removeWidget(self._page_view)
            self._page_view.deleteLater()

        if not page_view_state:
            return

        new_page_view = MapPageWidget(parent=self,
                                      initial_state=page_view_state)
        self._page_view = new_page_view
        self.ui.centralContainer.layout().addWidget(new_page_view)
        # Must be visible to accept focus, so queue on the main loop
        misli.call_delayed(new_page_view.setFocus)

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
        new_note = TextNote(page_id=page_widget.state().page_id)
        new_note.x = note_pos.x()
        new_note.y = note_pos.y()
        actions.note.create_new_note(self.state(), new_note)

    def create_new_page_command(self):
        mouse_pos = self.cursor().pos()
        edit_window_pos = Point2D(mouse_pos.x(), mouse_pos.y())
        tab_actions.create_new_page(self.state(), edit_window_pos)
