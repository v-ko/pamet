from PySide2.QtWidgets import QVBoxLayout, QWidget
from PySide2.QtCore import Qt

from misli import misli
from misli.gui.component import Component
from ..notes import usecases


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

            self._page_component = misli.create_components_for_page(
                self.current_page_id, parent_id=self.id)
            self.layout().addWidget(self._page_component)

    def add_child(self, child_id):
        child = misli.component(child_id)

        # If we're adding an edit component
        if child.obj_class in misli.components_lib.edit_component_names():

            # Abort any ongoing editing
            if self._edit_component:
                usecases.abort_editing_note(self._edit_component.id)

            # Setup the editing component
            self._edit_component = child
            child.setParent(self)
            child.setWindowFlag(Qt.Sheet, True)

            child.show()

    def remove_child(self, child_id):
        child = misli.component(child_id)
        if child.obj_class == 'TextEdit':
            self._edit_component = None
            child.hide()
