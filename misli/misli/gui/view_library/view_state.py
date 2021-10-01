from typing import Any

from misli import Entity
from misli import register_entity


def register_view_state_type(view_state_class: Any):
    return register_entity(view_state_class)


class ViewState(Entity):
    pass
