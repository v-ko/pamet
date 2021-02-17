from PySide2.QtWidgets import QMainWindow, QPushButton
from PySide2.QtGui import QIcon

from misli.dataclasses import dataclass, Entity
import misli_gui
from misli_gui.base_component import Component

from pamet_desktop import usecases


from .ui_browser_window import Ui_BrowserWindow

# from pamet_desktop.browser_tab import BrowserTabComponent

BROWSER_WINDOW_COMPONENT = 'BrowserWindow'


@dataclass
class BrowserWindowComponentState(Entity):
    obj_class: str = BROWSER_WINDOW_COMPONENT
    app_id: str = None
    tab_ids: set = set


class BrowserWindowComponent(QMainWindow, Component):
    def __init__(self, parent_id):
        QMainWindow.__init__(self)
        Component.__init__(
            self,
            parent_id=parent_id,
            default_state=BrowserWindowComponentState(),
            obj_class=BROWSER_WINDOW_COMPONENT)

        self._tabs = {}  # By id

        self.ui = Ui_BrowserWindow()
        self.ui.setupUi(self)

        self.menuButton = QPushButton(QIcon.fromTheme('menu'), '')
        self.ui.tabWidget.setCornerWidget(self.menuButton)
        self.ui.tabWidget.currentChanged.connect(
            self.handle_tab_changed)

        # for tab_id in component.tab_ids:
        #     self._add_tab(tab_id)
    #
    # def handle_component_update(self, component):
    #     if self.component.tab_ids == component.tab_ids:
    #         return
    #
    #     added_tab_ids = component.tab_ids - self.component.tab_ids
    #     removed_tab_ids = self.component.tab_ids - component.tab_ids
    #
    #     for added_tab_id in added_tab_ids:
    #         self._add_tab(added_tab_id)
    #
    #     for removed_tab_id in removed_tab_ids:
    #         self._remove_tab(removed_tab_id)

    def handle_child_changes(self, added, removed, updated):
        for child in added:
            self.handle_child_added(child)

        for child in removed:
            self.handle_child_removed(child)

    def handle_child_added(self, tab):
        self.ui.tabWidget.addTab(tab, tab.state().name)

    def handle_child_updated(self, old_tab_state, new_state):
        if old_tab_state.name != new_state.name:
            tab = misli_gui.component(old_tab_state.id)
            tab_idx = self.ui.tabWidget.indexOf(tab)
            self.ui.tabWidget.setTabText(tab_idx, new_state.name)

    # def _add_tab(self, tab_id):
    #     tab_component = misli_gui.component(tab_id)
    #
    #     self._tabs[tab_component.id] = tab_component
    #     tab = BrowserTab(tab_component)
    #     page_id = tab.page_component.page()
    #     self.ui.tabWidget.addTab(tab, page_id)

    def handle_child_removed(self, child):
        tab_idx = self.ui.tabWidget.indexOf(child)
        self.ui.tabWidget.removeTab(tab_idx)

    def handle_tab_changed(self, index: int):
        self.ui.tabWidget.widget(0).update()

    # def add_child(self, child: Component):
    #     if child.obj_class == 'BrowserTab':
    #         self.ui.tabWidget.addTab(child, child.current_page_id)

    def update(self):
        pass

    def closeEvent(self, close_event):
        usecases.close_browser_window(self.id)
