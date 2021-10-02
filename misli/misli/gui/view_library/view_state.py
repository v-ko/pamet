from typing import Any
# from dataclasses import field

from misli import Entity
from misli import register_entity_type


def register_view_state_type(view_state_class: Any):
    return register_entity_type(view_state_class)


@register_view_state_type
class ViewState(Entity):
    mapped_entity: Entity = None
