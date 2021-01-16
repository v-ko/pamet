from typing import Callable
from collections import defaultdict

import misli
from misli.logging import BColors
from misli.entities import BaseEntity
from misli.helpers import get_new_id, find_many_by_props, find_one_by_props

from . import components_lib
from .actions_lib import Action
from .base_component import Component

log = misli.get_logger(__name__)


_components = {}
_component_ids_by_entity_id = defaultdict(list)
_entity_id_by_component_id = {}

_components_for_update = []
_pages_for_saving = set()

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


@log.traced
def _handle_actions():
    if not _actions_for_dispatch:
        return

    for handler in _action_handlers:
        handler([a.to_dict() for a in _actions_for_dispatch])

    _actions_for_dispatch.clear()


# Runtime component interface
@log.traced
def _add_component(component: Component):
    _components[component.id] = component


@log.traced
def create_component(obj_class: str, parent_id: str, id=None):
    ComponentClass = components_lib.get(obj_class)
    _component = ComponentClass(parent_id=parent_id)
    _component.id = id or get_new_id()

    _add_component(_component)

    if parent_id:
        component(parent_id).add_child(_component)

    return _component


@log.traced
def register_component_with_entity(
        component: Component, _entity: BaseEntity, index_id):
    _component_ids_by_entity_id[(_entity.id, index_id)].append(component.id)
    _entity_id_by_component_id[component.id] = (_entity.id, index_id)


@log.traced
def unregister_component_from_entities(component: Component):
    if component.id in _entity_id_by_component_id:
        entity_id, index_id = _entity_id_by_component_id[component.id]
        _component_ids_by_entity_id[(entity_id, index_id)].remove(component.id)
        del _entity_id_by_component_id[component.id]


@log.traced
def entity_for_component(component_id: str):
    if component_id in _entity_id_by_component_id:
        entity_id, index_id = _entity_id_by_component_id[component_id]
        return misli.entity(entity_id, index_id)


@log.traced
def components_for_entity(entity_id: str, index_id):
    if (entity_id, index_id) in _component_ids_by_entity_id:
        return [component(eid)
                for eid in _component_ids_by_entity_id[(entity_id, index_id)]]

    return []


@log.traced
def component(id: str):
    return _components[id]


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
def update_component(component_id: str):
    if component_id not in _components_for_update:
        _components_for_update.append(component_id)
    misli.call_delayed(_update_components, 0)


@log.traced
def remove_component(component_id: str):
    _component = component(component_id)

    if _component.parent_id:
        parent = component(_component.parent_id)
        parent.remove_child(_component)

    # Unregister _component
    unregister_component_from_entities(_component)


@log.traced
def _update_components():
    for component_id in _components_for_update:
        component(component_id).update()

    _components_for_update.clear()
