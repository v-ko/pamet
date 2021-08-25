import time
import functools
from typing import Union
from enum import Enum

import misli
from misli import gui
from misli.helpers import get_new_id
log = misli.get_logger(__name__)


ACTIONS = {}
_actions_stack = []


def action(name: str):
    """A decorator that adds an action state emission on the start and end of
    each function call (via misli.gui.push_action).

    On module initialization this decorator saves the decorated function in the
     actions library (by name). By registering actions and providing a stream
     of action states it's possible to later replay the app usage.

    Args:
        name (str): The name of the action (domain-like naming convention, e.g.
         'context.action_name')
    """
    def decorator_action(func):

        @functools.wraps(func)
        def wrapper_action(*args, **kwargs):

            _action = Action(
                name, ActionRunStates.STARTED, args=list(args), kwargs=kwargs)

            gui.push_action(_action)

            # Call the actual function
            func(*args, **kwargs)

            _action.duration = time.time() - _action.start_time
            _action.run_state = ActionRunStates.FINISHED
            gui.push_action(_action.copy())

        if name in ACTIONS:
            raise Exception(f'An action with the name {name} is already'
                            f' registered')

        ACTIONS[name] = wrapper_action

        return wrapper_action
    return decorator_action


class ActionRunStates(Enum):
    STARTED = 1
    FINISHED = 2


class Action:
    """Mostly functions as a data class to carry the action state, args, kwargs
     and profiling info.
    """
    def __init__(
            self,
            name,
            run_state=ActionRunStates.STARTED,
            args=None,
            kwargs=None,
            id=None,
            start_time=None,
            duration=-1):

        self.name = name
        self.run_state = None
        self.set_run_state(run_state)

        self.args = []
        self.set_args(args)

        self.kwargs = kwargs or {}

        self.id = id or get_new_id()
        self.start_time = start_time if start_time is not None else time.time()
        self.duration = duration

    def set_run_state(self, run_state: Union[ActionRunStates, str]):
        if isinstance(run_state, ActionRunStates):
            self.run_state = run_state
        else:
            self.run_state = ActionRunStates[run_state]

    def set_args(self, args: Union[tuple, list]):
        if isinstance(args, tuple):
            args = list(args)
        elif not isinstance(args, list):
            raise ValueError

        self.args = args

    def __repr__(self):
        return ('<Action name=%s run_state=%s id=%s>' %
                (self.name, self.run_state.name, self.id))

    def copy(self) -> 'Action':
        return Action(**vars(self))

    def asdict(self) -> dict:
        self_dict = vars(self)
        self_dict['run_state'] = self.run_state.name
        return self_dict
