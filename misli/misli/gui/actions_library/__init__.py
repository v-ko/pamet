import time
import functools
from typing import Callable

import misli
from misli import gui

log = misli.get_logger(__name__)

_actions_by_name = {}
_names_by_wrapped_func = {}
_unwrapped_action_funcs_by_name = {}


def is_registered(action_function: Callable):
    return action_function in _names_by_wrapped_func


def unwrapped_action_function(action_name: str):
    return _unwrapped_action_funcs_by_name[action_name]


def name_for_wrapped_function(function: Callable):
    return _names_by_wrapped_func[function]


from misli.gui.actions_library.action import Action, ActionRunStates


def execute_action(_action):
    _action.run_state = ActionRunStates.STARTED
    gui.log_action_state(_action)

    # We get an action context (i.e. push this action on the stack)
    # Mainly in order to handle action nesting and do view updates
    # only after the completion of the top-level(=root) action.
    # That way redundant GUI rendering is avoided inside an action that
    # makes multiple update_state calls and/or invokes other actions
    with gui.action_context(_action):
        # Call the actual function
        return_val = _action.function(*_action.args, **_action.kwargs)

    _action.duration = time.time() - _action.start_time
    _action.run_state = ActionRunStates.FINISHED
    gui.log_action_state(_action.copy())

    return return_val


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
    if not name or not isinstance(name, str):
        raise Exception(
            'Please add the action name as an argument to the decorator. '
            'E.g. @action(\'action_name\')')

    def decorator_action(func):
        @functools.wraps(func)
        def wrapper_action(*args, **kwargs):
            _action = Action(name,
                             args=list(args),
                             kwargs=kwargs)

            if misli.gui.view_and_parent_update_ongoing():
                log.debug(f'Cannot invoke an action while updating the views.'
                          f' Queueing {_action} on the main loop.')
                misli.dispatch(_action, gui.ACTIONS_QUEUE_CHANNEL)
                return

            return execute_action(_action)

        if name in _unwrapped_action_funcs_by_name:
            raise Exception(f'An action with the name {name} is already'
                            f' registered')

        _actions_by_name[name] = wrapper_action
        _names_by_wrapped_func[wrapper_action] = name
        _unwrapped_action_funcs_by_name[name] = func

        return wrapper_action

    return decorator_action
