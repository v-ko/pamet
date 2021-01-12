from typing import Callable, List
from collections import defaultdict

import misli
from misli.entities.change import ChangeTypes
from misli.core.logging import BColors
from misli.entities import Page, Note, BaseEntity, Change
from misli.gui.actions_lib import Action
from misli.gui.base_component import Component
from misli.helpers import get_new_id, find_many_by_props, find_one_by_props
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
    ComponentClass = misli.gui.components_lib.get(obj_class)
    _component = ComponentClass(parent_id=parent_id)
    _component.id = id or get_new_id()

    _add_component(_component)

    if parent_id:
        component(parent_id).add_child(_component)

    return _component


@log.traced
def _register_component_with_entity(
        component: Component, base_object: BaseEntity):
    _component_ids_by_entity_id[base_object.id].append(component.id)
    _entity_id_by_component_id[component.id] = base_object.id


@log.traced
def _unregister_component_from_entities(component: Component):
    if component.id in _entity_id_by_component_id:
        base_object_id = _entity_id_by_component_id[component.id]
        _component_ids_by_entity_id[base_object_id].remove(component.id)
        del _entity_id_by_component_id[component.id]


@log.traced
def entity_for_component(component_id: str):
    if component_id in _entity_id_by_component_id:
        return misli.entity(_entity_id_by_component_id[component_id])


@log.traced
def components_for_entity(entity_id: str):
    if entity_id in _component_ids_by_entity_id:
        return [component(eid)
                for eid in _component_ids_by_entity_id[entity_id]]

    return []


@log.traced
def create_components_for_page(page_id: str, parent_id: str):
    page = misli.page(page_id)
    page_component = create_component(
        obj_class=page.obj_class, parent_id=parent_id)

    page_component.set_props_from_entity(**page.state())
    _register_component_with_entity(page_component, page)

    for note in page.notes():
        create_component_for_note(
            page.id, note.id, note.obj_class, page_component.id)

    return page_component


@log.traced
def create_component_for_note(
        page_id: str, note_id: str, obj_class: str, parent_id: str):

    component = create_component(obj_class, parent_id)
    note = misli.page(page_id).note(note_id)
    component.set_props_from_entity(**note.state())

    _register_component_with_entity(component, note)
    return component


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
    _unregister_component_from_entities(_component)


# I should consider refactoring those when I implement Changes (undo, etc)
# They might go into a reducer-like pattern (configured in main() ) but
# that should happen when needed and not earlier
@log.traced
def _update_components_for_note_change(note_change: Change):
    note = Note(**note_change.last_state())

    if note_change.type == ChangeTypes.CREATE:
        page_components = components_for_entity(
            note.page_id)

        # Create a note component for all opened views for its page
        for pc in page_components:
            create_component_for_note(
                note.page_id, note.id, note.obj_class, pc.id)

            update_component(pc.id)

    elif note_change.type == ChangeTypes.UPDATE:
        note_components = components_for_entity(note.id)
        for nc in note_components:
            nc.set_props_from_entity(**note.state())

            # Hacky cache clearing
            nc.should_rebuild_pcommand_cache = True
            nc.should_reallocate_image_cache = True
            nc.should_rerender_image_cache = True

            update_component(nc.id)

    elif note_change.type == ChangeTypes.DELETE:
        note_components = components_for_entity(note.id)
        for nc in note_components:
            remove_component(nc.id)

        page_components = components_for_entity(
            note.page_id)

        for pc in page_components:
            update_component(pc.id)


@log.traced
def _update_components_for_page_change(page_change: Change):
    page_state = page_change.last_state()
    page = Page(**page_state)

    if page_change.type == ChangeTypes.CREATE:
        pass

    elif page_change.type == ChangeTypes.UPDATE:
        page_components = components_for_entity(page.id)
        for pc in page_components:
            pc.set_props_from_entity(**page_state)
            update_component(pc.id)

    elif page_change.type == ChangeTypes.DELETE:
        raise NotImplementedError


@log.traced
def update_components_from_changes(changes: List[Change]):
    for change in changes:
        obj_type = change.last_state()['obj_type']

        if obj_type == 'Note':
            _update_components_for_note_change(change)

        elif obj_type == 'Page':
            _update_components_for_page_change(change)

        else:
            raise NotImplementedError


@log.traced
def _update_components():
    for component_id in _components_for_update:
        component(component_id).update()

    _components_for_update.clear()
