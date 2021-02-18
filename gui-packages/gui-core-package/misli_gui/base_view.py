from __future__ import annotations

from misli.helpers import get_new_id
from misli.dataclasses import Entity
import misli_gui
from misli import get_logger
log = get_logger(__name__)


class View:
    def __init__(self, parent_id: str, initial_model: Entity, obj_class: str):
        initial_model.id = get_new_id()
        self.parent_id = parent_id
        self.obj_class = obj_class
        self.__last_model = initial_model

    @property
    def id(self):
        return self.__last_model.id

    @property
    def last_model(self):
        return self.__last_model

    def update_cached_model(self, new_model):
        self.__last_model = new_model

    def handle_model_update(self, old_model, new_model):
        pass

    def handle_child_changes(
            self, children_added, children_removed, children_updated):
        pass

    def child(self, child_id: str):
        return misli_gui.view(child_id)

    def get_children(self):
        return misli_gui.view_children(self.id)
