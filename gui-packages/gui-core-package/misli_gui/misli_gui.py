from typing import Callable
from collections import defaultdict

import misli
from misli.logging import BColors
from misli.change import Change
from misli.helpers import get_new_id, find_many_by_props, find_one_by_props

from . import components_lib
from .actions_lib import Action
from .base_component import Component

log = misli.get_logger(__name__)

COMPONENTS_CHANNEL = '__components__'
misli.add_channel(COMPONENTS_CHANNEL)

_components = {}
_components_per_parent = {}

# _entity_connections[channel][entity_id] = List[(component_id, handler)]
# _entity_connections = defaultdict(defaultdict(list))

_components_for_addition = []
_components_for_removal = []
_added_components_per_parent = defaultdict(list)
_removed_components_per_parent = defaultdict(list)
_updated_components = []
_old_component_states = {}
# _pages_for_saving = set()

_action_handlers = []
_actions_for_dispatch = []


# Action channel interface
def push_action(action: Action):
    args_str = ', '.join([str(a) for a in action.args])
    kwargs_str = ', '.join(['%s=%s' % (k, v)
                            for k, v in action.kwargs.items()])

    green = BColors.OKGREEN
    end = BColors.ENDC

    log.info(
        'Action %s%s %s%s ARGS=*(%s) KWARGS=**{%s}' %
        (green, action.run_state.name, action.name, end, args_str, kwargs_str))

    _actions_for_dispatch.append(action)
    misli.call_delayed(_handle_actions, 0)


# The first action state returned is the top-level action start state
# The rest of the states are nested in it and won't invoke a separate on_action
# By the same logic the last action returned is the Finished state of the
# top-level action
@log.traced
def on_action(handler: Callable):
    _action_handlers.append(handler)


# @log.traced
def _handle_actions():
    if not _actions_for_dispatch:
        return

    for handler in _action_handlers:
        handler([a.to_dict() for a in _actions_for_dispatch])

    _actions_for_dispatch.clear()


# Runtime component interface
@log.traced
def create_component(obj_class, *args, **kwargs):
    _component = components_lib.create_component(obj_class, *args, **kwargs)
    add_component(_component)
    return _component


def add_component(_component: Component):
    # _components_for_addition.append(_component)
    _components[_component.id] = _component
    _components_per_parent[_component.id] = []

    if _component.parent_id:
        if _component.parent_id not in _components_per_parent:
            raise Exception(
                'Cannot add component with missing parent with id: %s' %
                _component.parent_id)

        _added_components_per_parent[_component.parent_id].append(_component)
        _components_per_parent[_component.parent_id].append(_component)
        # parent = component(_component.parent_id)
        # parent.handle_child_added(_component)

    # _added_components.append(_component)

    misli.call_delayed(_update_components, 0)


# @log.traced
# def add_component_immediate(_component: Component):
    # if not _component.id:
    #     _component.id = get_new_id()

    # change = Change.CREATE(_component.asdict())
    # misli.dispatch(change.asdict(), COMPONENTS_CHANNEL)


# @log.traced
def component(id: str):
    if id not in _components:
        return None
    return _components[id]


def component_state(component_id):
    return component(component_id).state()


def component_children(component_id):
    return _components_per_parent[component_id]


@log.traced
def components():
    return [c for c_id, c in _components.items()]


@log.traced
def find_components(**props):
    return find_many_by_props(_components, **props)


@log.traced
def find_component(**props):
    return find_one_by_props(_components, **props)


@log.traced
def update_component_state(new_state):
    _component = component(new_state.id)
    old_state = _component.state()
    _component._set_state(new_state)

    if _component.id not in _old_component_states:
        _old_component_states[_component.id] = old_state

    if _component not in _updated_components:
        _updated_components.append(_component)

    # if component_id in _component_state_changes:
    #     _component_state_changes[component_id].update(changes)
    #     return

    # _component = component(component_id)
    # component_state = _component.state
    # component_state.replace(changes)

    # _component_state_changes[component_id] = changes
    misli.call_delayed(_update_components, 0)


# def _update_component_immediate(component_id):
#     _component = component(component_id)
#     # old_state = _component.state
#     # new_state = _component_state_changes[component_id]

#     # _component.apply_state_change(new_state)

#     old_state = _old_component_states[component_id]
#     new_state = _component.state()

#     if _component.parent_id:
#         parent = component(_component.parent_id)
#         parent.handle_child_updated(old_state, new_state)

#     # change = Change.UPDATE(old_state.asdict(), new_state.asdict())
#     # misli.dispatch(change.asdict(), COMPONENTS_CHANNEL)


def remove_component(_component: Component):
    _components_for_removal.append(_component)

    del _components_per_parent[_component.id]
    del _components[_component.id]

    if _component.parent_id:
        if _component.parent_id not in _components_per_parent:
            raise Exception(
                'Cannot add component with missing parent with id: %s' %
                _component.parent_id)

        _components_per_parent[_component.parent_id].remove(_component)
        _removed_components_per_parent[_component.parent_id].append(_component)

    misli.call_delayed(_update_components, 0)


# @log.traced
# def remove_component_immediate(_component: str):
#     # if not _component:
#     #     raise Exception('Cannot remove missing component with id %s' %
#     #                     _component.id)

#     if _component.parent_id:
#         _components_per_parent[_component.parent_id].remove(_component)
#         parent = component(_component.parent_id)
#         parent.handle_child_removed(_component)

#     del _components[_component.id]
#     # change = Change.DELETE(_component.asdict())
#     # misli.dispatch(change.asdict(), COMPONENTS_CHANNEL)


# @log.traced
def _update_components():
    # (added, removed, updated)
    child_changes_per_parent_id = defaultdict(lambda: ([], [], []))

    for _component in _updated_components:
        # add_component_immediate(_component)
        old_state = _old_component_states[_component.id]
        _component.handle_state_update(old_state, _component.state())

        if _component.parent_id:
            child_changes_per_parent_id[_component.parent_id][2].append(
                _component)

    for parent_id, added in _added_components_per_parent.items():
        child_changes_per_parent_id[parent_id][0].extend(added)

    for parent_id, removed in _removed_components_per_parent.items():
        child_changes_per_parent_id[parent_id][1].extend(removed)

    _updated_components.clear()
    _added_components_per_parent.clear()
    _removed_components_per_parent.clear()

    for component_id, changes in child_changes_per_parent_id.items():
        _component = component(component_id)
        _component.handle_child_changes(*changes)

# Should be subscribed to the COMPONENTS_CHANNEL in the module init
# def apply_component_changes(changes):
#     for change in changes:
#         state_dict = change.last_state()
#         _component = component(state_dict['id'])

#         if change.is_create():
#             parent_id = _component.parent_id
#             if parent_id:
#                 parent = component(parent_id)
#                 parent.handle_child_added(_component)

#         elif change.is_update():
#             _component.apply_state_change(state_dict)

#         elif change.is_delete():
#             parent_id = state_dict['parent_id']
#             if parent_id:
#                 parent = component(parent_id)
#                 parent.handle_child_removed(_component)


# misli.subscribe(COMPONENTS_CHANNEL, apply_component_changes)
