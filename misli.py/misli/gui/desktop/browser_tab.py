from PySide2.QtWidgets import QVBoxLayout, QWidget
from PySide2.QtCore import Qt

import misli
from misli.gui.base_component import Component
from .. import usecases


class BrowserTabComponent(QWidget, Component):
    def __init__(self, parent_id):
        QWidget.__init__(self)
        Component.__init__(self, parent_id, obj_class='BrowserTab')

        self.setLayout(QVBoxLayout())
        self._page_component = None
        self.current_page_id = ''
        self._edit_component = None

    def current_page_component(self):
        return self._page_component

    def update(self):
        if not self.current_page_id and not self._page_component:
            return

        pc_id = ''
        if self._page_component:
            pc_id = self._page_component.id

        if self.current_page_id and self.current_page_id != pc_id:
            if self._page_component:
                self.layout().removeWidget(self._page_component)

            self._page_component = misli.gui.create_components_for_page(
                self.current_page_id, parent_id=self.id)
            self.layout().addWidget(self._page_component)

    def add_child(self, child):
        # If we're adding an edit component
        if child.obj_class in misli.gui.components_lib.edit_component_names():

            # Abort any ongoing editing
            if self._edit_component:
                usecases.abort_editing_note(self._edit_component.id)

            # Setup the editing component
            self._edit_component = child
            child.setParent(self)
            child.setWindowFlag(Qt.Sheet, True)

    def remove_child(self, child):
        if child.obj_class == 'TextEdit':
            self._edit_component = None
            child.hide()

        Component.remove_child(self, child)
