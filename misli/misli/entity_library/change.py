from enum import Enum

from misli.entity_library.entity import Entity


class ChangeTypes(Enum):
    CREATE = 1
    UPDATE = 2
    DELETE = 3


class Change:
    """An object representing a change in the entity state. It holds the old
     and the new states (as entities) as well as the change type.
    """
    def __init__(
            self,
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

        if not (self.old_state or self.new_state):
            raise ValueError('Both old and new state are None.')

    def asdict(self) -> dict:
        return dict(
            type=str(self.type),
            old_state=self.old_state.asdict() if self.old_state else None,
            new_state=self.new_state.asdict() if self.new_state else None,
        )

    @classmethod
    def CREATE(cls, state: Entity) -> 'Change':
        """Convenience method for constructing a Change with type CREATE"""
        return cls(
            type=ChangeTypes.CREATE, new_state=state)

    @classmethod
    def UPDATE(cls, old_state: Entity, new_state: Entity) -> 'Change':
        """Convenience method for constructing a Change with type UPDATE"""
        return cls(
            type=ChangeTypes.UPDATE,
            old_state=old_state,
            new_state=new_state)

    @classmethod
    def DELETE(cls, old_state: Entity) -> 'Change':
        """Convenience method for constructing a Change with type DELETE"""
        return cls(
            type=ChangeTypes.DELETE, old_state=old_state)

    def __repr__(self) -> str:
        return (f'<Change type={self.type} old_state={self.old_state} '
                f'new_state={self.new_state}>')

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

