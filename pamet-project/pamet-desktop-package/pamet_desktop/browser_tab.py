from dataclasses import dataclass

from PySide2.QtWidgets import QVBoxLayout, QWidget
from PySide2.QtCore import Qt

from misli import Entity
import misli_gui
from misli_gui.base_view import View
from pamet import view_library
from pamet.note_components import usecases


@dataclass
class BrowserTabViewState(Entity):
    name: str = ''
    page_view_id: str = None


class BrowserTabView(QWidget, View):
    view_class = 'BrowserTab'

    def __init__(self, parent_id):
        QWidget.__init__(self)
        View.__init__(
            self,
            parent_id=parent_id,
            initial_model=BrowserTabViewState()
        )

        self.page_view = None
        self._edit_view = None

        # Widget config
        self.setLayout(QVBoxLayout())

    def handle_model_update(self, old_state, new_state):
        if old_state.page_view_id != new_state.page_view_id:
            if new_state.page_view_id:
                self.switch_to_page_view(new_state.page_view_id)

            else:
                raise Exception('Empty page_view_id passed')

    def handle_child_changes(self, added, removed, updated):
        for child in added:
            self.add_child(child)

        for child in removed:
            self.remove_child(child)

    def add_child(self, child):
        # If we're adding an edit component
        if child.view_class in view_library.edit_view_names():

            # Abort any ongoing editing
            if self._edit_view:
                usecases.abort_editing_note(self._edit_view.id)

            # Setup the editing component
            self._edit_view = child
            child.setParent(self)
            child.setWindowFlag(Qt.Sheet, True)
            child.show()

    def remove_child(self, child):
        if child.view_class in view_library.edit_view_names():
            self._edit_view = None
            child.close()

    def switch_to_page_view(self, page_view_id):
        if self.page_view:
            self.layout().removeWidget(self.page_view)

        page_view = misli_gui.view(page_view_id)
        self.layout().addWidget(page_view)

        self.page_view = page_view
