import time
import functools
from enum import Enum

import misli
from misli.helpers import get_new_id
log = misli.get_logger(__name__)


ACTIONS = {}


def action(_type):
    def decorator_action(func):

        @functools.wraps(func)
        def wrapper_action(*args, **kwargs):

            action = ActionObject(
                _type, ActionRunStates.STARTED, args=list(args), kwargs=kwargs)
            misli.gui.push_action(action.to_dict())

            # Call the actual function
            func(*args, **kwargs)

            action.duration = time.time() - action.start_time
            action.run_state = ActionRunStates.FINISHED
            misli.gui.push_action(action.to_dict())

        ACTIONS[_type] = wrapper_action
        return wrapper_action

    return decorator_action


class ActionRunStates(Enum):
    STARTED = 1
    FINISHED = 2


class ActionObject:
    def __init__(
            self,
            type,
            run_state=ActionRunStates.STARTED,
            args=None,
            kwargs=None,
            id=None,
            start_time=None,
            duration=-1):

        self.type = type
        self.run_state = None
        self.set_run_state(run_state)

        self.args = []
        self.set_args(args)

        self.kwargs = kwargs or {}

        self.id = id or get_new_id()
        self.start_time = start_time if start_time is not None else time.time()
        self.duration = duration

    def set_run_state(self, run_state):
        if type(run_state) == ActionRunStates:
            self.run_state = run_state
        else:
            self.run_state = ActionRunStates[run_state]

    def set_args(self, args):
        if type(args) == tuple:
            args = list(args)
        elif type(args) != list:
            raise ValueError

        self.args = args

    def __repr__(self):
        s = ('<ActionObject run_state=%s id=%s type=%s args=%s '
             'kwargs=%s>' % (self.run_state, self.id, self.type,
                             self.args, self.kwargs))
        return s

    def to_dict(self):
        self_dict = vars(self).copy()
        self_dict['run_state'] = self.run_state.name
        return self_dict
