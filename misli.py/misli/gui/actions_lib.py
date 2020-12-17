import time
import uuid
import functools
from enum import Enum

import misli


ACTIONS = {}


def action(name):
    def decorator_action(func):
        @functools.wraps(func)
        def wrapper_action(*args, **kwargs):
            action_start = ActionState(
                name, ActionStateTypes.STARTED, args=args, kwargs=kwargs)
            misli.gui.push_action(action_start)

            func(*args, **kwargs)

            action_end = ActionState(
                name,
                ActionStateTypes.FINISHED,
                id=action_start.id,
                args=args,
                kwargs=kwargs)
            misli.gui.push_action(action_end)

        return wrapper_action

    ACTIONS[name] = decorator_action

    return decorator_action


class ActionStateTypes(Enum):
    STARTED = 1
    FINISHED = 2


class ActionState:
    def __init__(self, action_name, type, id=None, args=None, kwargs=None):
        self.action_name = action_name
        self.type = type
        self.args = args
        self.kwargs = kwargs
        self.id = id

        if self.id is None:
            self.id = str(uuid.uuid4())[:8]

        if self.args is None:
            self.args = []

        if self.kwargs is None:
            self.kwargs = {}

        self.time = time.time()

        # self.finish_time = None

        # if state == ActionStates.STARTED:
        #     self.start_time = time.time()

        # else:
        #     self.finish_time = time.time()

    # def __repr__(self):
    #     return str(vars(self))

    def to_dict(self):
        self_dict = vars(self)
        self_dict['type'] = self.type.name
        return self_dict
