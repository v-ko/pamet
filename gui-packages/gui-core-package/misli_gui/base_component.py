from __future__ import annotations

from misli.helpers import get_new_id
from misli.dataclasses import Entity
import misli_gui
from misli import get_logger
log = get_logger(__name__)


class Component():
    def __init__(self, parent_id: str, default_state: Entity, obj_class: str):
        default_state.id = get_new_id()
        self.parent_id = parent_id
        self.obj_class = obj_class
        # misli_gui.add_compoenent(self)
        self.__state = default_state

    # def __del__(self):
    #     misli_gui.remove_component(self)

    @property
    def id(self):
        return self.__state.id

    @property
    def _state(self):
        return self.__state

    def state(self):
        return self.__state.copy()

    def set_state(self, **changes):
        misli_gui.update_component(self.id, **changes)

    def _set_state(self, new_state):
        # old_state = self.__state
        self.__state = new_state
        # self.handle_state_update(old_state, new_state)

    # def add_child(self, child):
    #     # self.__children.append(child)

    #     self.handle_child_added(child)

    # def remove_child(self, child):

    def handle_state_update(self, old_state, new_state):
        pass

    # def handle_child_added(self, child):
    #     pass

    # def handle_child_removed(self, child):
    #     pass

    # def handle_child_updated(self, old_state, new_state):
    #     pass

    def handle_child_changes(
            self, children_added, children_removed, children_updated):
        pass

    # @log.traced
    # def add_child(self, child: Component):

    # @log.traced
    # def remove_child(self, child: Component):
    #     if child.id not in self.__children:
    #         return

    #     del self.__children[child.id]

    def child(self, child_id: str):
        return misli_gui.component(child_id)

    def get_children(self):
        # return [c for cid, c in self.__children.items()]
        return misli_gui.component_children(self.id)
