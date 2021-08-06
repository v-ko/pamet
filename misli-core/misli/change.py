from enum import Enum


class ChangeTypes(Enum):
    CREATE = 1
    UPDATE = 2
    DELETE = 3


class Change:
    """An object representing a change in the entity state. It holds the old
     and the new states (as dicts) as well as the change type.
    """
    def __init__(
            self,
            type: ChangeTypes,
            old_state: dict = None,
            new_state: dict = None):
        """Construct a change object. When the change is of type CREATE or
        DELETE - the old_state or new_state respectively should naturally be
        omitted.

        Raises:
            Exception: Missing id attribute of either entity state.
        """
        self.type = type
        self.old_state = old_state or {}
        self.new_state = new_state or {}

        if not (self.old_state or self.new_state):
            raise ValueError('Both old and new state are None.')

        if 'id' not in self.last_state():
            raise Exception('Changes can only carry Entities or at least '
                            'objects with an "id" attribute')

    def asdict(self):
        return vars(self)

    @classmethod
    def CREATE(cls, state):
        """Convenience method for constructing a Change with type CREATE"""
        return cls(
            _type=ChangeTypes.CREATE, old_state={}, new_state=state)

    @classmethod
    def UPDATE(cls, old_state, new_state):
        """Convenience method for constructing a Change with type UPDATE"""
        return cls(
            _type=ChangeTypes.UPDATE,
            old_state=old_state,
            new_state=new_state)

    @classmethod
    def DELETE(cls, old_state):
        """Convenience method for constructing a Change with type DELETE"""
        return cls(
            _type=ChangeTypes.DELETE, old_state=old_state, new_state={})

    def __repr__(self):
        return '<Change type=%s>' % self.type

    def is_create(self) -> bool:
        return self.type == ChangeTypes.CREATE

    def is_update(self) -> bool:
        return self.type == ChangeTypes.UPDATE

    def is_delete(self) -> bool:
        return self.type == ChangeTypes.DELETE

    def last_state(self) -> dict:
        """Returns the latest available state.

        Returns:
            [dict]: If the change is of type UPDATE - returns new_state.
                    Otherwise returns whatever is available (for CREATE -
                    new_state and for DELETE - the old_state)
        """
        if not self.new_state:
            return self.old_state

        return self.new_state

