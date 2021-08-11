from typing import Callable
from collections import defaultdict
import time
import random

import misli
from misli.logging import BColors
from misli.helpers import find_many_by_props, find_one_by_props

from .actions_lib import Action
from .base_view import View

log = misli.get_logger(__name__)

ACTIONS_CHANNEL = '__ACTIONS__'
COMPONENTS_CHANNEL = '__COMPONENTS__'
misli.add_channel(ACTIONS_CHANNEL)
misli.add_channel(COMPONENTS_CHANNEL)

_views = {}
_views_per_parent = {}

_added_views_per_parent = defaultdict(list)
_removed_views_per_parent = defaultdict(list)
_updated_views = set()

_view_models = {}
_old_view_models = {}
_displayed_view_models = {}


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

    misli.dispatch(action, ACTIONS_CHANNEL)


@log.traced
def on_action(handler: Callable):
    misli.subscribe(ACTIONS_CHANNEL, handler)


def add_view(_view: View, initial_model):
    _views[_view.id] = _view
    _views_per_parent[_view.id] = []
    _view_models[_view.id] = initial_model
    _displayed_view_models[_view.id] = initial_model

    if _view.parent_id:
        if _view.parent_id not in _views_per_parent:
            raise Exception(
                'Cannot add component with missing parent with id: %s' %
                _view.parent_id)

        _added_views_per_parent[_view.parent_id].append(_view)
        _views_per_parent[_view.parent_id].append(_view)

    misli.call_delayed(_update_views, 0)


# @log.traced
def view(id: str):
    if id not in _views:
        return None
    return _views[id]


def view_model(view_id):
    if view_id not in _view_models:
        return None
    _view_model = _view_models[view_id]
    return _view_model.copy()


def displayed_view_model(view_id: str):
    if view_id not in _displayed_view_models:
        return None
    _view_model = _displayed_view_models[view_id]
    return _view_model.copy()


def view_children(view_id):
    return _views_per_parent[view_id]


@log.traced
def views():
    return [c for c_id, c in _views.items()]


@log.traced
def find_views(**props):
    return find_many_by_props(_views, **props)


@log.traced
def find_view(class_name: str = '', **props):
    if class_name:
        found = [v for view_id, v in _views.items()
                 if type(v).__name__ == class_name]
        if not found:
            return None
        return found[0]
    else:
        return find_one_by_props(_views, **props)


@log.traced
def update_view_model(new_model):
    _view: View = view(new_model.id)
    old_model = _view.displayed_model
    _view_models[_view.id] = new_model

    if _view.id not in _old_view_models:
        _old_view_models[_view.id] = old_model

    _updated_views.add(_view)
    misli.call_delayed(_update_views, 0)


def remove_view(_view: View):
    _views_per_parent.pop(_view.id)
    _views.pop(_view.id)

    if _view.parent_id:
        if _view.parent_id not in _views_per_parent:
            raise Exception(
                'Cannot add component with missing parent with id: %s' %
                _view.parent_id)

        _views_per_parent[_view.parent_id].remove(_view)
        _removed_views_per_parent[_view.parent_id].append(_view)

    misli.call_delayed(_update_views, 0)


# @log.traced
def _update_views():
    # (added, removed, updated)
    child_changes_per_parent_id = defaultdict(lambda: ([], [], []))

    for _view in _updated_views:
        old_model = _old_view_models[_view.id]
        new_model = view_model(_view.id)
        _displayed_view_models[_view.id] = new_model
        _view.handle_model_update(old_model, new_model)

        if _view.parent_id:
            child_changes_per_parent_id[_view.parent_id][2].append(
                _view)

    for parent_id, added in _added_views_per_parent.items():
        child_changes_per_parent_id[parent_id][0].extend(added)

    for parent_id, removed in _removed_views_per_parent.items():
        child_changes_per_parent_id[parent_id][1].extend(removed)

    _updated_views.clear()
    _added_views_per_parent.clear()
    _removed_views_per_parent.clear()
    _old_view_models.clear()

    for view_id, changes in child_changes_per_parent_id.items():
        _view = view(view_id)
        _view.handle_child_changes(*changes)


# ----------------Various---------------------
def set_reproducible_ids(enabled):
    if enabled:
        random.seed(0)
    else:
        random.seed(time.time())


class EntityToViewMapping:
    def __init__(self):
        self._view_ids_by_entity_id = defaultdict(list)
        self._entity_id_by_view_id = {}

    def map_entity_to_view(self, entity_gid, view_id):
        self._view_ids_by_entity_id[entity_gid].append(view_id)
        self._entity_id_by_view_id[view_id] = entity_gid

    def unmap_entity_from_view(self, entity_gid, view_id):
        if view_id not in self._entity_id_by_view_id:
            raise Exception('Cannot unregister component that is not '
                            'registered ' % view_id)

        self._view_ids_by_entity_id[entity_gid].remove(view_id)
        del self._entity_id_by_view_id[view_id]

    def views_mapped_to_entity(self, entity_gid):
        component_ids = self._view_ids_by_entity_id[entity_gid]

        components = []
        for component_id in component_ids:
            component = view(component_id)
            if not component:
                self.unmap_entity_from_view(entity_gid, component_id)
                continue

            components.append(component)
        return components
