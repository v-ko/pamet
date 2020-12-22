from enum import Enum


class ChangeTypes(Enum):
    CREATE = 1
    UPDATE = 2
    DELETE = 3


class Change:
    def __init__(self, change_type, old_state=None, new_state=None):
        if old_state is None:
            old_state = {}
        if new_state is None:
            new_state = {}

        self.type = change_type
        self.old_state = old_state
        self.new_state = new_state

    def __repr__(self):
        return '<Change type=%s>' % self.type

    def last_state(self):
        if self.new_state:
            return self.new_state
        elif self.old_state:
            return self.old_state
        else:
            raise ValueError('Both old and new states are empty')
