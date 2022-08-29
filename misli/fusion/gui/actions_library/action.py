from copy import copy
import time
from typing import Union, Callable
from enum import Enum

from fusion.helpers import get_new_id
from fusion.gui.actions_library import unwrapped_action_by_name


class ActionRunStates(Enum):
    NONE = 0
    STARTED = 1
    FINISHED = 2


class ActionCall:
    """Mostly functions as a data class to carry the action state, args, kwargs
     and profiling info.
    """
    def __init__(self,
                 name: str,
                 run_state: Union[ActionRunStates,
                                  str] = ActionRunStates.NONE,
                 args: list = None,
                 kwargs: dict = None,
                 id: str = None,
                 start_time: float = None,
                 duration: int = -1,
                 function: Callable | str = None):

        self.name = name
        self.run_state = None
        self.set_run_state(run_state)

        self.args = args or []
        if not isinstance(self.args, list):
            self.args = list(self.args)

        self.kwargs = kwargs or {}

        self.id = id or get_new_id()
        self.start_time = start_time if start_time is not None else time.time()
        self.duration = duration
        if function and isinstance(function, str):
            function = unwrapped_action_by_name(function)
        self._function = function

    @property
    def function(self):
        if not self._function:
            self._function = unwrapped_action_by_name(self.name)

        return self._function

    def set_run_state(self, run_state: Union[ActionRunStates, str]):
        if isinstance(run_state, ActionRunStates):
            self.run_state = run_state
        else:
            self.run_state = ActionRunStates[run_state]

    def __repr__(self):
        string = (f'<Action name={self.name} run_state={self.run_state} '
                  f'id={self.id}')
        if self.duration != -1:
            string += f'duration={self.duration:.2f}'
        return string + '>'

    def copy(self) -> 'ActionCall':
        return ActionCall(**self.asdict())

    def asdict(self) -> dict:
        self_dict = copy(vars(self))
        self_dict['run_state'] = self.run_state.name
        self_dict.pop('_function')
        return self_dict
