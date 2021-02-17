from PySide2.QtWidgets import QVBoxLayout, QWidget
from PySide2.QtCore import Qt

# import misli
# from misli import Change
from misli.dataclasses import dataclass, Entity
import misli_gui
from misli_gui.base_component import Component

from pamet.note_components import usecases

BROWSER_TAB = 'BrowserTab'


@dataclass
class BrowserTabComponentState(Entity):
    name: str = ''
    page_component_id: str = None


class BrowserTabComponent(QWidget, Component):
    def __init__(self, parent_id):
        QWidget.__init__(self)
        Component.__init__(
            self,
            parent_id=parent_id,
            default_state=BrowserTabComponentState(),
            obj_class=BROWSER_TAB)

        # Init from component
        # if self.state.page_component_id:
        #     self.switch_to_page_component(component.page_component_id)

        # misli.subscribe_to_entity(
        #     misli_gui.COMPONENTS_CHANNEL,
        #     self.component.id,
        #     self.handle_component_change)

        self.page_component = None
        self._edit_component = None

        # Widget config
        self.setLayout(QVBoxLayout())

    # def handle_component_change(self, message: dict):
    #     change = Change(**message)
    #     if change.is_update():
    #         component = change.last_state()
    #         self.handle_component_update(component)

    def handle_state_update(self, old_state, new_state):
        if old_state.page_component_id != new_state.page_component_id:
            if new_state.page_component_id:
                self.switch_to_page_component(new_state.page_component_id)

            else:
                raise Exception('Empty page_component_id passed')

    def handle_child_changes(self, added, removed, updated):
        for child in added:
            pass
            self.add_child(child)

        for child in removed:
            self.remove_child(child)

    # def update(self):
    #     if not self.component.page_component_id and not self.page_component:
    #         return

    #     pc_id = None
    #     if :
    #         pc_id = self.page_component.id

    #     if self.page_component_id != self.page_component.id:

    #         self.page_component = pamet.create_components_for_page(
    #             self.page_component_id, parent_id=self.id)
    #         self.layout().addWidget(self.page_component)

    def switch_to_page_component(self, page_component_id):
        if self.page_component:
            self.layout().removeWidget(self.page_component)

        page_component = misli_gui.component(page_component_id)
        self.layout().addWidget(page_component)

        self.page_component = page_component

    def add_child(self, child: Component):
        # If we're adding an edit component
        if child.obj_class in misli_gui.components_lib.edit_component_names():

            # Abort any ongoing editing
            if self._edit_component:
                usecases.abort_editing_note(self._edit_component.id)

            # Setup the editing component
            self._edit_component = child
            child.setParent(self)
            child.setWindowFlag(Qt.Sheet, True)
            child.show()

    def remove_child(self, child: Component):
        if child.obj_class in misli_gui.components_lib.edit_component_names():
            self._edit_component = None
            child.close()
