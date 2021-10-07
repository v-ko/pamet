from typing import Callable, Union, List
from collections import defaultdict
import time
import random
from contextlib import contextmanager

import misli
from misli import Entity, Change
from misli.logging import BColors
from misli.helpers import find_many_by_props

from .actions_library import Action, execute_action
from .view_library.view import View, ViewState
from .model_to_view_binder.entity_to_view_mapper import EntityToViewMapping

log = misli.get_logger(__name__)

ACTIONS_QUEUE_CHANNEL = '__ACTIONS_QUEUE__'
ACTIONS_LOG_CHANNEL = '__ACTIONS_LOG__'
ENTITY_CHANGE_CHANNEL = '__ENTITY_CHANGES__'
misli.add_channel(ACTIONS_QUEUE_CHANNEL)
misli.add_channel(ACTIONS_LOG_CHANNEL)
misli.add_channel(ENTITY_CHANGE_CHANNEL)


def execute_action_queue(actions: List[Action]):
    for action in actions:
        execute_action(action)


misli.subscribe(ACTIONS_QUEUE_CHANNEL, execute_action_queue)

_views = {}
_views_per_parent = {}

_added_views_per_parent = defaultdict(list)
_removed_views_per_parent = defaultdict(list)
_updated_views = set()

_view_states = {}
_previous_view_states = {}
_displayed_view_states = {}

_action_context_stack = []
_view_and_parent_update_ongoing = False

mapping = EntityToViewMapping()


def view_and_parent_update_ongoing():
    return _view_and_parent_update_ongoing


@contextmanager
def action_context(action):
    _action_context_stack.append(action)
    yield None

    # If it's a root action - propagate the state changes to the views (async)
    _action_context_stack.pop()
    if not _action_context_stack:
        misli.call_delayed(_update_views, 0)


def ensure_context():
    if not _action_context_stack:
        raise Exception(
            'State changes can only happen in functions decorated with the '
            'misli.gui.actions_library.action decorator')


# def broadcast_change(change: Change):
#     misli.dispatch(change, ENTITY_CHANGE_CHANNEL)


# Action channel interface
def log_action_state(action: Action):
    """Push an action to the actions channel and handle logging. Should only be
    called by the action decorator.
    """
    args_str = ', '.join([str(a) for a in action.args])
    kwargs_str = ', '.join(
        ['%s=%s' % (k, v) for k, v in action.kwargs.items()])

    green = BColors.OKGREEN
    end = BColors.ENDC

    log.info(
        'Action %s%s %s%s ARGS=*(%s) KWARGS=**{%s}' %
        (green, action.run_state.name, action.name, end, args_str, kwargs_str))

    misli.dispatch(action, ACTIONS_LOG_CHANNEL)


@log.traced
def on_actions_logged(handler: Callable):
    """Register a callback to the actions channel. It will be called before and
    after each action call. It's used for user interaction recording.

    Args:
        handler (Callable): The callable to be invoked on each new message on
        the channel
    """
    misli.subscribe(ACTIONS_LOG_CHANNEL, handler)


def publish_entity_change(change: Change):
    misli.dispatch(ENTITY_CHANGE_CHANNEL, change)


def on_entity_changes(handler: Callable):
    misli.subscribe(ENTITY_CHANGE_CHANNEL, handler)


def add_view(_view: View, initial_state):
    """Register a view instance in misli.gui. Should only be called in
    View.__init__.
    """
    ensure_context()
    _views[_view.id] = _view
    _views_per_parent[_view.id] = []
    _view_states[_view.id] = initial_state
    _displayed_view_states[_view.id] = initial_state

    if _view.parent_id:
        if _view.parent_id not in _views_per_parent:
            raise Exception(
                'Cannot add component with missing parent with id: %s' %
                _view.parent_id)

        _added_views_per_parent[_view.parent_id].append(_view)
        _views_per_parent[_view.parent_id].append(_view)

    misli.call_delayed(_update_views, 0)


def create_view(parent_id,
                view_class_name: str = '',
                view_class_metadata_filter: dict = None,
                mapped_entity: Entity = None):
    view_class_metadata_filter = view_class_metadata_filter or {}
    view_class = misli.gui.view_library.get_view_class(
        view_class_name, **view_class_metadata_filter)
    _view: View = view_class(parent_id=parent_id)
    _view_state = _view.state

    # # Update the view state with the supplied initial data
    # for key, val in state_update_dict.items():
    #     setattr(_view_state, key, val)

    if mapped_entity:
        _view_state.mapped_entity = mapped_entity.copy()
        mapping.map(mapped_entity.gid(), _view.id)

    update_state(_view_state)
    return _view


# @log.traced
def view(id: str) -> Union[View, None]:
    """Get a view instance by its id

    Args:
        id (str): The view id

    Returns:
        Union[View, None]: Returns the view object (a subclass of View). If
        a view with that id is not found - the function returns None
    """
    if id not in _views:
        return None
    return _views[id]


def previous_view_state(view_id: str) -> Union[ViewState, None]:
    """Get a copy of the view model corresponding to the view with the given id.

    This function returns a copy of the view model that was last dispatched to
    the view. I.e. if any actions have made changes since then - they will not
    be present in the old ViewModel as returned by this method.

    Args:
        view_id (str): The id of the view model (same as its view)

    Returns:
        Entity: A copy of the view model (should be a subclass of Entity). If
        there's no model found for that id - the function returns None.
    """
    if view_id not in _previous_view_states:
        return None
    _view_state = _previous_view_states[view_id]
    return _view_state.copy()


def view_state(view_id: str) -> Union[ViewState, None]:
    """Get a copy of the view model corresponding to the view with the given id.

    Mind that if we're in the middle of a user action this model can be updated,
    but not yet passed to the View.

    Args:
        view_id (str): The id of the view model (same as its view)

    Returns:
        Entity: A copy of the view model (should be a subclass of Entity). If
        there's no model found for that id - the function returns None.
    """
    if view_id not in _view_states:
        return None
    _view_state = _view_states[view_id]
    return _view_state.copy()


def displayed_view_state(view_id: str) -> Union[ViewState, None]:
    """Get the last displayed view model for the view with id == view_id.

    This is the last copy of the view model that has been passed to the View
    in a View.handle_model_update call. This means that if we're in the middle
    of a user action that has called misli.gui.update_view_model, the updates
    will not yet be reflected in the model returned by this function.

    Args:
        view_id (str): The id of the view model (same as its view)

    Returns:
        Entity: A copy of the view model (should be a subclass of Entity). If
        there's no model found for that id - the function returns None.
    """
    if view_id not in _displayed_view_states:
        return None
    _view_state = _displayed_view_states[view_id]
    return _view_state.copy()


def view_children(view_id: str) -> List[View]:
    """Returns a list of the children of the view with an id == view_id.

    Args:
        view_id (str): The id of the view (that we want the children of)

    Returns:
        List[View]: A list of _
    """
    return _views_per_parent[view_id]


@log.traced
def views() -> List[View]:
    """Get all view instances registered in misli.gui"""
    return [c for c_id, c in _views.items()]


@log.traced
def find_views(class_name: str = None, filter_dict: dict = None) -> List[View]:
    """Get all views with the given class name that have attributes with values
    that fulfill the filter.

    Args:
        class_name (str, optional): If specified - only the views with a class
            with the given name are returned.
        filter (dict, optional): Key/value pairs that must be present as
            attribute/values in the view to include it in the results.

    Returns:
        List[View]: A list of Views
    """
    filter_dict = filter_dict or {}

    if class_name:
        found = [
            v for view_id, v in _views.items()
            if type(v).__name__ == class_name
        ]
        if not found:
            return []

        return list(find_many_by_props(found, **filter_dict))

    else:
        return list(find_many_by_props(_views, **filter_dict))


# @log.traced
# def find_view(class_name: str = '', **props):
#     """Find a single view by class name or by matching its attributes by the
#     supplied keyword arguments"""
#     if class_name:
#         found = [v for view_id, v in _views.items()
#                  if type(v).__name__ == class_name]
#         if not found:
#             return None
#         return found[0]
#     else:
#         return find_one_by_props(_views, **props)


@log.traced
def update_state(new_state: ViewState):
    """Replace the view model with an updated one. A view update will be
    invoked as a next task on the main loop.

    Args:
        new_state (view model, inherits Entity): the model with updated
        properties. It's identified by its id (so that must be intact).
    """
    ensure_context()
    if not isinstance(new_state, ViewState):
        raise Exception('Expected a ViewState')

    _view: View = view(new_state.id)
    previous_state = _view.state
    _view_states[_view.id] = new_state

    if _view.id not in _previous_view_states:
        _previous_view_states[_view.id] = previous_state

    _updated_views.add(_view)
    misli.call_delayed(_update_views, 0)


def remove_view(_view: View):
    """Remove a view from the GUI tree. It's parent will be notified.

    Args:
        _view (View): The view to be removed

    Raises:
        Exception: If the view provided is not registered with misli.gui
    """
    ensure_context()
    _views_per_parent.pop(_view.id)
    _views.pop(_view.id)

    if _view.parent_id:
        if _view.parent_id not in _views_per_parent:
            raise Exception(
                'Cannot add component with missing parent with id: %s' %
                _view.parent_id)

        _views_per_parent[_view.parent_id].remove(_view)
        _removed_views_per_parent[_view.parent_id].append(_view)


# @log.traced
def _update_views():
    """An internal function that relays the view state changes to the views
    once the user action logic has completed exectution.
    """
    global _view_and_parent_update_ongoing
    _view_and_parent_update_ongoing = True  # Restricts action invokation

    # (added, removed, updated)
    child_changes_per_parent_id = defaultdict(lambda: ([], [], []))

    for _view in _updated_views:
        _displayed_view_states[_view.id] = view_state(_view.id)
        _view.handle_state_update()

        if _view.parent_id:
            child_changes_per_parent_id[_view.parent_id][2].append(_view)

    for parent_id, added in _added_views_per_parent.items():
        child_changes_per_parent_id[parent_id][0].extend(added)

    for parent_id, removed in _removed_views_per_parent.items():
        child_changes_per_parent_id[parent_id][1].extend(removed)

    _updated_views.clear()
    _added_views_per_parent.clear()
    _removed_views_per_parent.clear()
    _previous_view_states.clear()

    for view_id, changes in child_changes_per_parent_id.items():
        _view = view(view_id)
        _view.handle_child_changes(*changes)

    _view_and_parent_update_ongoing = False


# ----------------Various---------------------
def set_reproducible_ids(enabled: bool):
    """When testing - use non-random ids"""
    if enabled:
        random.seed(0)
    else:
        random.seed(time.time())
