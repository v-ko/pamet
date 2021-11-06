from typing import List
from PySide6.QtWidgets import QVBoxLayout, QWidget
from PySide6.QtCore import Qt

import misli
from misli import gui
from misli.gui.view_library import register_view_type

from pamet.views.map_page.view import MapPageView

from .view import BrowserTabView, SIDEBAR_WIDTH, MIN_TAB_WIDTH


@register_view_type
class BrowserTabWidget(QWidget, BrowserTabView):
    def __init__(self, parent_id):
        QWidget.__init__(self)
        BrowserTabView.__init__(self, parent_id)

        self_rect = self.geometry()
        self.right_sidebar = QWidget(self)
        self.right_sidebar.setLayout(QVBoxLayout())
        self.right_sidebar.setAutoFillBackground(True)
        right_sidebar_rect = self.right_sidebar.geometry()
        right_sidebar_rect.setWidth(SIDEBAR_WIDTH)
        right_sidebar_rect.setHeight(self_rect.height())
        right_sidebar_rect.setTopRight(self_rect.topRight())
        self.right_sidebar.setGeometry(right_sidebar_rect)

        self._page_view = None
        self._page_subscription_id = None

        # Widget config
        self.setMinimumWidth(MIN_TAB_WIDTH)
        self.setLayout(QVBoxLayout())

    def resizeEvent(self, event):
        # Update the sidebar position
        self_rect = self.geometry()
        right_sidebar_rect = self.right_sidebar.geometry()
        right_sidebar_rect.moveTopRight(self_rect.topRight())
        right_sidebar_rect.setHeight(self_rect.height())
        self.right_sidebar.setGeometry(right_sidebar_rect)

    def on_state_update(self):
        new_state = self.state()
        prev_state = self.previous_state()

        if not self.page_view() or \
                (prev_state.page_view_id != new_state.page_view_id):
            if new_state.page_view_id:
                self.switch_to_page_view(new_state.page_view_id)

            else:
                raise Exception('Empty page_view_id passed')

        if prev_state.right_sidebar_view_id != new_state.right_sidebar_view_id:
            old_view = misli.gui.view(prev_state.right_sidebar_view_id)
            if old_view:
                self.right_sidebar.layout().removeWidget(old_view)

            if new_state.right_sidebar_view_id:
                new_view = misli.gui.view(new_state.right_sidebar_view_id)
                self.right_sidebar.layout().addWidget(new_view)


        if new_state.right_sidebar_visible:
            self.right_sidebar.show()
            self.right_sidebar.raise_()
        else:
            self.right_sidebar.hide()

    def on_child_added(self, child):
        # If we're adding an edit component
        if type(child) in gui.view_library.get_view_classes(edit=True):
            # Setup the editing component
            child.setParent(self)
            child.setWindowFlag(Qt.Sheet, True)

            child.show()

    def on_child_removed(self, child):
        if type(child) in gui.view_library.get_view_classes(edit=True):
            child.close()

        else:
            child.deleteLater()

    def on_child_updated(self, child):
        if isinstance(child, MapPageView):
            page_view_state = child.state()
            window = self.get_parent()
            self_idx = window.ui.tabWidget.indexOf(self)
            window.ui.tabWidget.setTabText(self_idx, page_view_state.page.name)

    def switch_to_page_view(self, page_view_id):
        if self._page_view:
            self.layout().removeWidget(self._page_view)

        new_page_view = misli.gui.view(page_view_id)
        self._page_view = new_page_view
        self.layout().addWidget(new_page_view)
        # Must be visible to accept focus, so queue on the main loop
        misli.call_delayed(new_page_view.set_focus)
