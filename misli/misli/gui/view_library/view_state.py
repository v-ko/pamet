from __future__ import annotations
from dataclasses import field
from typing import Any

from misli import Entity
from misli import entity_type
from misli import gui


def view_state_type(view_state_class: Any):
    return entity_type(view_state_class, repr=False)


@view_state_type
class ViewState(Entity):
    _added: bool = field(default=False, repr=False)
    _version: int = field(default=0, repr=False)
    # backup: ViewState = field(default=None, repr=False)

    def __setattr__(self, attr_name, value):
        if self._added and not gui.is_in_action():
            raise Exception('View states can be modified only in actions')
            # return

        Entity.__setattr__(self, attr_name, value)

    def __repr__(self) -> str:
        return f'{type(self).__name__} id={self.id}'
