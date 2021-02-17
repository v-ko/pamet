from enum import Enum
from misli.dataclasses import dataclass, Entity


class ChangeTypes(Enum):
    CREATE = 1
    UPDATE = 2
    DELETE = 3


class Change:
    change_type: ChangeTypes
    old_state: dict = dict
    new_state: dict = dict

    def __init__(
            self,
            change_type: ChangeTypes,
            old_state: dict = None,
            new_state: dict = None):

        self.change_type = change_type
        self.old_state = old_state or {}
        self.new_state = new_state or {}

        if 'id' not in self.last_state():
            raise Exception('Changes can only carry Entities or at least '
                            'objects with an "id" attribute')

    def asdict(self):
        return vars(self)

    @classmethod
    def CREATE(cls, state):
        return cls(
            change_type=ChangeTypes.CREATE, old_state={}, new_state=state)

    @classmethod
    def UPDATE(cls, old_state, new_state):
        return cls(
            change_type=ChangeTypes.UPDATE,
            old_state=old_state,
            new_state=new_state)

    @classmethod
    def DELETE(cls, old_state):
        return cls(
            change_type=ChangeTypes.DELETE, old_state=old_state, new_state={})

    def __repr__(self):
        return '<Change type=%s>' % self.change_type

    def is_create(self):
        return self.change_type == ChangeTypes.CREATE

    def is_update(self):
        return self.change_type == ChangeTypes.UPDATE

    def is_delete(self):
        return self.change_type == ChangeTypes.DELETE

    def last_state(self):
        if self.new_state:
            return self.new_state
        elif self.old_state:
            return self.old_state
        else:
            raise ValueError('Both old and new states are empty')
