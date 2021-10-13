from typing import Any
# from dataclasses import field

from misli import Entity
from misli import wrap_and_register_entity_type
from misli import gui


def wrap_and_register_view_state_type(view_state_class: Any):
    return wrap_and_register_entity_type(view_state_class)


@wrap_and_register_view_state_type
class ViewState(Entity):
    mapped_entity: Entity = None
    parent_id: str = None

    def view(self):
        return gui.view(self.id)
