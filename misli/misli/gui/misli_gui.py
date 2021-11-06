from typing import Callable, Union, List, Any
import time
import random
from contextlib import contextmanager

import misli
from misli import Entity, Change
from misli.logging import BColors
from misli.helpers import find_many_by_props

from .actions_library import Action, execute_action, name_for_wrapped_function
from .view_library.view import View, ViewState
from .model_to_view_binder.entity_to_view_mapper import EntityToViewMapping

log = misli.get_logger(__name__)

ACTIONS_QUEUE_CHANNEL = '__ACTIONS_QUEUE__'
ACTIONS_LOG_CHANNEL = '__ACTIONS_LOG__'

misli.add_channel(ACTIONS_QUEUE_CHANNEL)
misli.add_channel(ACTIONS_LOG_CHANNEL)

STATE_CHANGE_BY_ID_CHANNEL = '__STATE_CHANGES_BY_ID__'
STATE_CHANGE_BY_PARENT_CHANNEL = '__STATE_CHANGES_BY_PARENT__'

misli.add_channel(STATE_CHANGE_BY_ID_CHANNEL,
                  index_key=lambda x: x.last_state().id)
misli.add_channel(STATE_CHANGE_BY_PARENT_CHANNEL,
                  index_key=lambda x: x.last_state().parent_id)


def execute_action_queue(actions: List[Action]):
    for action in actions:
        execute_action(action)


misli.subscribe(ACTIONS_QUEUE_CHANNEL, execute_action_queue)

_views = {}
_views_per_parent = {None: []}

_updated_views = set()
_added_views = set()
_removed_views = set()
_last_updates_removed_views = {}

_view_states = {}
_previous_view_states = {}
_displayed_view_states = {}

_action_context_stack = []
_view_and_parent_update_ongoing = False

_util_provider = None
mapping = EntityToViewMapping()


def util_provider():
    return _util_provider


def set_util_provider(provider):
    global _util_provider
    _util_provider = provider


def view_and_parent_update_ongoing():
    return _view_and_parent_update_ongoing


@contextmanager
def lock_actions():
    global _view_and_parent_update_ongoing
    _view_and_parent_update_ongoing = True
    yield None
    _view_and_parent_update_ongoing = False


@contextmanager
def action_context(action):
    _action_context_stack.append(action)
    yield None

    # If it's a root action - propagate the state changes to the views (async)
    _action_context_stack.pop()
    if not _action_context_stack:
        misli.call_delayed(_dipatch_state_changes, 0)


def is_in_action():
    return bool(_action_context_stack)


def ensure_context():
    if not is_in_action():
        raise Exception(
            'State changes can only happen in functions decorated with the '
            'misli.gui.actions_library.action decorator')


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
    msg = (f'Action {green}{action.run_state.name} {action.name}{end} '
           f'ARGS=*({args_str}) KWARGS=**{{{kwargs_str}}}')
    if action.duration != -1:
        msg += f' time={action.duration * 1000:.2f}ms'
    log.info(msg)

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


def queue_action(action_func, args: list = None, kwargs: dict = None):
    action = Action(name_for_wrapped_function(action_func))
    action.args = args or []
    action.kwargs = kwargs or {}
    misli.dispatch(action, ACTIONS_QUEUE_CHANNEL)


@log.traced
def add_view(_view: View):
    ensure_context()
    initial_state = _view._View__state
    _views[_view.id] = _view
    _views_per_parent[_view.id] = []
    _view_states[_view.id] = initial_state
    _added_views.add(_view)
    _views_per_parent[_view.parent_id].append(_view)

    if _view.parent_id and (_view.parent_id not in _views_per_parent):
        raise Exception(
            'Cannot add component with missing parent with id: %s' %
            _view.parent_id)

    _view.subscribtions.append(
        misli.subscribe(STATE_CHANGE_BY_ID_CHANNEL,
                        _view._handle_state_changes,
                        index_val=initial_state.id))

    _view.subscribtions.append(
        misli.subscribe(STATE_CHANGE_BY_PARENT_CHANNEL,
                        _view._handle_children_state_changes,
                        index_val=initial_state.id))

    misli.call_delayed(_dipatch_state_changes, 0)


@log.traced
def create_view(parent_id,
                view_class_name: str = '',
                view_class_metadata_filter: dict = None,
                mapped_entity: Entity = None,
                init_kwargs: dict = None):
    init_kwargs = init_kwargs or {}
    view_class_metadata_filter = view_class_metadata_filter or {}

    view_class = misli.gui.view_library.get_view_class(
        view_class_name, **view_class_metadata_filter)
    _view: View = view_class(parent_id=parent_id, **init_kwargs)

    add_view(_view)
    _view_state = _view.state()

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


def removed_view(view_id):
    return _last_updates_removed_views[view_id]


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
        return view(view_id)
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
    return view(view_id)._View__state


def view_children(view_id: str) -> List[View]:
    """Returns a list of the children of the view with an id == view_id.

    Args:
        view_id (str): The id of the view (that we want the children of)

    Returns:
        List[View]: A list of _
    """
    return _views_per_parent[view_id].copy()


@log.traced
def views() -> List[View]:
    """Get all view instances registered in misli.gui"""
    return list(_views.values())


@log.traced
def find_views(**filter) -> List[View]:
    type_name = filter.pop('type_name', None)
    # type = ...
    parent_id = filter.pop('parent_id', None)

    found = _views.copy()

    if parent_id:
        found = view_children(parent_id)

    if type_name:
        found = [
            v for view_id, v in _views.items()
            if type(v).__name__ == type_name
        ]
        if not found:
            return []

    if filter:
        return list(find_many_by_props(found, **filter))

    return found



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
    previous_state = _view.state()
    _view_states[_view.id] = new_state

    if _view.id not in _previous_view_states:
        _previous_view_states[_view.id] = previous_state

    _updated_views.add(_view)
    misli.call_delayed(_dipatch_state_changes, 0)


@log.traced
def remove_view(_view: View):
    """Remove a view from the GUI tree. It's parent will be notified.

    Args:
        _view (View): The view to be removed

    Raises:
        Exception: If the view provided is not registered with misli.gui
    """
    ensure_context()

    for child in _view.get_children():
        remove_view(child)

    for sub_id in _view.subscribtions:
        misli.unsubscribe(sub_id)

    _views_per_parent.pop(_view.id)
    _views.pop(_view.id)
    _removed_views.add(_view)

    if _view.parent_id:
        if _view.parent_id not in _views_per_parent:
            raise Exception(
                'Cannot add component with missing parent with id: %s' %
                _view.parent_id)

        _views_per_parent[_view.parent_id].remove(_view)


# @log.traced
def _dipatch_state_changes():
    global _removed_views
    global _last_updates_removed_views

    for _view in _added_views:
        # If the view happens to have been removed later in the same action
        if _view.id not in _views:
            continue
        elif _view in _removed_views:
            _removed_views.remove(_view)

        misli.dispatch(Change.CREATE(view_state(_view.id)),
                       STATE_CHANGE_BY_ID_CHANNEL)
        misli.dispatch(Change.CREATE(view_state(_view.id)),
                       STATE_CHANGE_BY_PARENT_CHANNEL)

    for _view in _updated_views:
        # If the view is removed after an update - skip it
        if _view.id not in _views:
            continue
        misli.dispatch(
            Change.UPDATE(previous_view_state(_view.id), view_state(_view.id)),
            STATE_CHANGE_BY_ID_CHANNEL)
        misli.dispatch(
            Change.UPDATE(previous_view_state(_view.id), view_state(_view.id)),
            STATE_CHANGE_BY_PARENT_CHANNEL)

    for _view in _removed_views:
        misli.dispatch(Change.DELETE(view_state(_view.id)),
                       STATE_CHANGE_BY_ID_CHANNEL)
        misli.dispatch(Change.DELETE(view_state(_view.id)),
                       STATE_CHANGE_BY_PARENT_CHANNEL)

    _updated_views.clear()
    _added_views.clear()
    _previous_view_states.clear()

    for _view in _removed_views:
        _last_updates_removed_views[_view.id] = _view
    _removed_views.clear()


# ----------------Various---------------------
def set_reproducible_ids(enabled: bool):
    """When testing - use non-random ids"""
    if enabled:
        random.seed(0)
    else:
        random.seed(time.time())


def focused_view() -> Union[View, None]:
    return _util_provider.focused_view()


def focused_view_or_parent(view_type: Any = None):
    _focused_view = focused_view()

    if not _focused_view:
        return None

    if not view_type:
        return _focused_view

    if isinstance(_focused_view, view_type):
        return _focused_view

    while _focused_view.parent_id:
        _focused_view = view(_focused_view.parent_id)
        if isinstance(_focused_view, view_type):
            return _focused_view

    # If we went up to the top level view and it's not of the view_type
    if not isinstance(_focused_view, view_type):
        return None

    return _focused_view


def handle_root_view_mounting(changes):
    for change in changes:
        if change.is_create():
            _util_provider.mount_view(change.last_state().view())
        elif change.is_delete():
            _util_provider.unmount_view(change.last_state().view())
