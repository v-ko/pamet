from PySide6.QtWidgets import QVBoxLayout, QWidget
from PySide6.QtCore import Qt

import misli
from misli import gui
from misli.gui.view_library import register_view_type

from .view import BrowserTabView


@register_view_type
class BrowserTabViewWidget(QWidget, BrowserTabView):
    def __init__(self, parent_id):
        QWidget.__init__(self)
        BrowserTabView.__init__(self, parent_id)
        # Widget config
        self.setLayout(QVBoxLayout())

    def on_state_update(self):
        new_model = self.state()

        if not self.page_view() or \
                (self.previous_state().page_view_id != new_model.page_view_id):
            if new_model.page_view_id:
                self.switch_to_page_view(new_model.page_view_id)

            else:
                raise Exception('Empty page_view_id passed')

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

    def switch_to_page_view(self, page_view_id):
        page_view = self.page_view()
        if page_view:
            self.layout().removeWidget(page_view)

        self.layout().addWidget(page_view)
        misli.call_delayed(page_view.set_focus)  # Must be visible to accept focus
