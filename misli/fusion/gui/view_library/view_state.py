from __future__ import annotations
from dataclasses import field
from typing import Any

from fusion import entity_type
from fusion import gui
from fusion.entity_library.entity import Entity
from fusion.helpers import get_new_id


def view_state_type(view_state_class: Any):
    return entity_type(view_state_class, repr=False)


@view_state_type
class ViewState(Entity):
    '''Mind putting this class as last inherited when also inheriting from
    an Entity with a custom id field.'''
    view_id: str = field(default_factory=get_new_id)
    _added: bool = field(default=False, init=False, repr=False)
    _version: int = field(default=0, init=False, repr=False)

    def __setattr__(self, attr_name, value):
        if self._added and not gui.is_in_action():
            raise Exception('View states can be modified only in actions')

        Entity.__setattr__(self, attr_name, value)

    def __repr__(self) -> str:
        return f'{type(self).__name__} view_id={self.view_id}'
