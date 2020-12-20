from collections import defaultdict

import misli
from misli.entities.change import ChangeTypes
from misli.helpers import get_new_id, find_many_by_props, find_one_by_props
from misli.gui.actions_lib import ActionObject
from ..entities import Page, Note
log = misli.get_logger(__name__)


_components = {}
_components_for_base_object = defaultdict(list)
_base_object_for_component = {}

_components_for_update = []
_pages_for_saving = set()

_action_handlers = []
_actions_for_dispatch = []


# Action channel interface
def push_action(action_state):
    log.info(str(ActionObject(**action_state)))
    _actions_for_dispatch.append(action_state)
    misli.call_delayed(_handle_actions, 0)


# The first action state returned is the top-level action start state
# The rest of the states are nested in it and won't invoke a separate on_action
# By the same logic the last action returned is the Finished state of the
# top-level action
def on_action(handler):
    _action_handlers.append(handler)


def _handle_actions():
    if not _actions_for_dispatch:
        return

    for handler in _action_handlers:
        handler(_actions_for_dispatch)

    _actions_for_dispatch.clear()


# Runtime component interface
def _add_component(component):
    _components[component.id] = component


def create_component(obj_class, parent_id, id=None):
    ComponentClass = misli.gui.components_lib.get(obj_class)
    _component = ComponentClass(parent_id=parent_id)
    _component.id = id or get_new_id()

    _add_component(_component)

    if parent_id:
        component(parent_id).add_child(_component)

    return _component


def _register_component_with_base_object(component, base_object):
    _components_for_base_object[base_object.id].append(component)
    _base_object_for_component[component.id] = base_object


def create_components_for_page(page_id, parent_id):
    page = misli.page(page_id)
    page_component = create_component(
        obj_class=page.obj_class, parent_id=parent_id)

    page_component.set_props_from_base_object(**page.state())
    _register_component_with_base_object(page_component, page)

    for note in page.notes():
        create_component_for_note(
            page.id, note.id, note.obj_class, page_component.id)

    return page_component


def create_component_for_note(
        page_id, note_id, obj_class, parent_id):

    component = create_component(obj_class, parent_id)
    note = misli.page(page_id).note(note_id)
    component.set_props_from_base_object(**note.state())

    _register_component_with_base_object(component, note)
    return component


def component(id):
    return _components[id]


def components():
    return [c for c_id, c in _components.items()]


def find_components(**props):
    return find_many_by_props(_components, **props)


def find_component(**props):
    return find_one_by_props(_components, **props)


def base_object_for_component(component_id):
    return _base_object_for_component[component_id]


def components_for_base_object(base_object_id):
    return _components_for_base_object[base_object_id]


def update_component(component_id: int):
    if component_id not in _components_for_update:
        _components_for_update.append(component_id)
    misli.call_delayed(_update_components, 0)


def remove_component(component_id):
    _component = component(component_id)

    if _component.parent_id:
        parent = component(_component.parent_id)
        parent.remove_child(_component)

    # Unregister _component
    if _component in _base_object_for_component:
        base_object = _base_object_for_component[_component]
        _components_for_base_object[base_object].remove(_component)
        del _base_object_for_component[_component]

    del _component


# I should consider refactoring those when I implement Changes (undo, etc)
# They might go into a reducer-like pattern (configured in main() ) but
# that should happen when needed and not earlier

def _update_components_for_note_change(note_change):
    note = Note(**note_change.last_state())

    if note_change.type == ChangeTypes.CREATE:
        page_components = components_for_base_object(
            note.page_id)

        # Create a note component for all opened views for its page
        for pc in page_components:
            create_component_for_note(
                note.page_id, note.id, note.obj_class, pc.id)

            update_component(pc.id)

    elif note_change.type == ChangeTypes.UPDATE:
        note_components = components_for_base_object(note.id)
        for nc in note_components:
            nc.set_props_from_base_object(**note.state())

            # Hacky cache clearing
            nc.should_rebuild_pcommand_cache = True
            nc.should_reallocate_image_cache = True
            nc.shoud_rerender_image_cache = True

            update_component(nc.id)

    elif note_change.type == ChangeTypes.DELETE:
        note_components = components_for_base_object(note.id)
        for nc in note_components:
            remove_component(nc.id)

        page_components = components_for_base_object(
            note.page_id)

        for pc in page_components:
            update_component(pc.id)


def _update_components_for_page_change(page_change):
    page_state = page_change.last_state()
    page = Page(**page_state)

    if page_change.type == ChangeTypes.CREATE:
        pass

    elif page_change.type == ChangeTypes.UPDATE:
        page_components = components_for_base_object(page.id)
        for pc in page_components:
            pc.set_props_from_base_object(**page_state)
            update_component(pc.id)

    elif page_change.type == ChangeTypes.DELETE:
        raise NotImplementedError


def update_components_from_changes(changes):
    for change in changes:
        obj_type = change.last_state()['obj_type']

        if obj_type == 'Note':
            _update_components_for_note_change(change)

        elif obj_type == 'Page':
            _update_components_for_page_change(change)

        else:
            raise NotImplementedError


def _update_components():
    for component_id in _components_for_update:
        component(component_id).update()

    _components_for_update.clear()
