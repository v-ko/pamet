from typing import Any
# from dataclasses import field

from misli import Entity
from misli import wrap_and_register_entity_type


def wrap_and_register_view_state_type(view_state_class: Any):
    return wrap_and_register_entity_type(view_state_class)


@wrap_and_register_view_state_type
class ViewState(Entity):
    mapped_entity: Entity = None
