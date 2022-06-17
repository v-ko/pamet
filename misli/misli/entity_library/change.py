from __future__ import annotations

from copy import copy
from enum import Enum
from typing import Any, Generator, Iterable

from misli import get_logger
from misli.entity_library.entity import Entity

log = get_logger(__name__)


class DiffTypes(Enum):
    ADDED = 1
    REMOVED = 2


class Diff:
    def __init__(self, change: Change, type: DiffTypes):
        self.change = change
        self.type = type

    def return_added(self, old_val, new_val):
        if not isinstance(old_val, Iterable) and isinstance(new_val, Iterable):
            raise Exception('Attribute type is not Iterable')

        for item in new_val:
            if item not in old_val:
                yield item

    def return_removed(self, old_val, new_val):
        # if isinstance(old_val, list) and isinstance(new_val, list):
        if not isinstance(old_val, Iterable) and isinstance(new_val, Iterable):
            raise Exception('Attribute type is not Iterable')

        for item in old_val:
            if item not in new_val:
                yield item

    def __getattr__(self, key) -> Generator[Any, None, None]:
        if not hasattr(self.change.new_state, key):
            raise AttributeError

        if self.change.is_create():
            pass
        elif self.change.is_delete():
            # Warning and empty
            log.error('Trying to get list/set diff for a deleted state.')
            # yield from []
        else:  # change.is_update()
            # if not hasattr(self.change.old_state, key):
            #     raise AttributeError
            pass

        old_val = getattr(self.change.old_state, key, [])
        new_val = getattr(self.change.new_state, key, [])

        if self.type == DiffTypes.ADDED:
            yield from self.return_added(old_val, new_val)

        else:  # self.type == DiffTypes.REMOVED:
            yield from self.return_removed(old_val, new_val)


class Updated:
    def __init__(self, change: Change):
        self.change = change

    def __getattr__(self, key):
        if self.change.is_create():
            if not hasattr(self.change.new_state, key):
                raise AttributeError
            else:
                return True

        elif self.change.is_delete():
            # Warning and empty
            log.error(f'Trying to infer if an attribute is updated for a'
                      f' deleted state. Change: {self.change}')
            return False

        else:  # is_update()
            if not hasattr(self.change.old_state, key):
                raise Exception

            if getattr(self.change.old_state, key) != \
                    getattr(self.change.new_state, key):
                return True
            else:
                return False


class ChangeTypes(Enum):
    CREATE = 1
    UPDATE = 2
    DELETE = 3


class Change:
    """An object representing a change in the entity state. It holds the old
     and the new states (as entities) as well as the change type.
    """
    def __init__(self,
                 type: ChangeTypes,
                 old_state: Entity = None,
                 new_state: Entity = None):
        """Construct a change object. When the change is of type CREATE or
        DELETE - the old_state or new_state respectively should naturally be
        omitted.

        Raises:
            Exception: Missing id attribute of either entity state.
        """
        self.type = type
        self.old_state = old_state
        self.new_state = new_state
        self.added = Diff(self, DiffTypes.ADDED)
        self.removed = Diff(self, DiffTypes.REMOVED)
        self.updated = Updated(self)

        if not (self.old_state or self.new_state):
            raise ValueError('Both old and new state are None.')

    def asdict(self) -> dict:
        return dict(
            type=str(self.type),
            old_state=self.old_state.asdict() if self.old_state else None,
            new_state=self.new_state.asdict() if self.new_state else None,
        )

    @classmethod
    def CREATE(cls, state: Entity) -> Change:
        """Convenience method for constructing a Change with type CREATE"""
        return cls(type=ChangeTypes.CREATE, new_state=copy(state))

    @classmethod
    def UPDATE(cls, old_state: Entity, new_state: Entity) -> Change:
        """Convenience method for constructing a Change with type UPDATE"""
        return cls(type=ChangeTypes.UPDATE,
                   old_state=copy(old_state),
                   new_state=copy(new_state))

    @classmethod
    def DELETE(cls, old_state: Entity) -> Change:
        """Convenience method for constructing a Change with type DELETE"""
        return cls(type=ChangeTypes.DELETE, old_state=copy(old_state))

    def __repr__(self) -> str:
        return (f'<Change type={self.type} {id(self)=} '
                f'old_state={self.old_state} new_state={self.new_state}>')

    def is_create(self) -> bool:
        return self.type == ChangeTypes.CREATE

    def is_update(self) -> bool:
        return self.type == ChangeTypes.UPDATE

    def is_delete(self) -> bool:
        return self.type == ChangeTypes.DELETE

    def last_state(self) -> Entity:
        """Returns the latest available state.

        Returns:
            [dict]: If the change is of type UPDATE - returns new_state.
                    Otherwise returns whatever is available (for CREATE -
                    new_state and for DELETE - the old_state)
        """
        if not self.new_state:
            return self.old_state

        return self.new_state
