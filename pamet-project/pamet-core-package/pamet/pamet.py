from typing import List
from dataclasses import replace

import misli
import pamet
from misli.change import Change, ChangeTypes
import misli_gui
from pamet.entities import Page, Note

from misli import get_logger
log = get_logger(__name__)


# -------------Pages CRUD-------------
def init_page(_page, notes: list):
    misli.create_entity_index(_page.id)
    for n in notes:
        misli.load_entity(n, n.page_id)


def deinit_page(_page):
    for n in notes(_page.id):
        misli.unload_entity(n, _page.id)
    misli.delete_entity_index(_page.id)


@log.traced
def add_page(_page, notes: list):
    init_page(_page, notes)
    misli.add_entity(_page, Page)


@log.traced
def load_page(_page: Page, notes: list):
    init_page(_page, notes)
    misli.load_entity(_page, Page)


@log.traced
def unload_page(page_id):
    _page = misli.entity(page_id, Page)
    if not _page:
        log.error('Cannot unload missing page with id "%s"' % page_id)
        return

    misli.unload_entity(_page, Page)


@log.traced
def pages():
    return misli.entities(Page)


def page(page_id: str):
    return misli.entity(page_id, Page)


@log.traced
def find_pages(**props):
    return misli.find_entity(Page, **props)


@log.traced
def find_page(**props):
    return misli.find_entities(Page, **props)


@log.traced
def update_page(**page_state):
    if 'id' not in page_state:
        log.error('Could not update note without a supplied id. '
                  'Given state: %s' % page_state)
        return

    page_id = page_state.pop('id')
    _page = page(page_id)
    if not _page:
        log.error('Cannot update missing page %s' % page_state['id'])
        return

    old_state = _page.state()
    old_state.update(page_state)
    new_page = Page(**old_state)
    misli.update_entity(new_page, Page)


@log.traced
def delete_page(page_id: str):
    _page = misli.entity(page_id, Page)
    if not _page:
        log.error('Cannot unload missing page with id "%s"' % page_id)
        return

    misli.unload_entity(_page, Page)
    misli.remove_entity(page_id, Page)


# -------------Notes CRUD-------------


@log.traced
def add_note(_note):
    if not _note.page_id:
        raise Exception(
            'Cannot create note without page_id. Note: %s' % _note)

    misli.add_entity(_note, _note.page_id)


def note(page_id: str, note_id: str):
    return misli.entity(note_id, page_id)


def notes(page_id):
    return misli.entities(page_id)


@log.traced
def remove_note(_note: Note):
    misli.remove_entity(_note, _note.page_id)


@log.traced
def update_note(**note_state):
    if 'page_id' not in note_state or 'id' not in note_state:
        log.error('Could not update note without id and page_id parameters. '
                  'Given state: %s' % note_state)
        return

    _note = Note(**note_state)
    # replace(_note, **note_state)
    old_state = _note.state()
    old_state.update(**note_state)
    misli.update_entity(Note(**old_state), _note.page_id)


@log.traced
def delete_note(_note: Note):
    misli.remove_entity(_note.id, _note.page_id)


# -------------------GUI stuff------------------------
@log.traced
def create_components_for_page(page_id: str, parent_id: str):
    _page = page(page_id)
    page_component = misli_gui.create_component(
        obj_class=_page.obj_class, parent_id=parent_id)

    page_component.set_props_from_entity(**_page.state())
    misli_gui.register_component_with_entity(page_component, _page, Page)

    for note in notes(_page.id):
        create_component_for_note(
            _page.id, note.id, note.obj_class, page_component.id)

    return page_component


@log.traced
def create_component_for_note(
        page_id: str, note_id: str, obj_class: str, parent_id: str):

    component = misli_gui.create_component(obj_class, parent_id)
    note = pamet.note(page_id, note_id)
    component.set_props_from_entity(**note.state())

    misli_gui.register_component_with_entity(component, note, note.page_id)
    return component


# I should consider refactoring those when I implement Changes (undo, etc)
# They might go into a reducer-like pattern (configured in main() ) but
# that should happen when needed and not earlier
@log.traced
def _update_components_for_note_change(note_change: Change):
    note = Note(**note_change.last_state())

    if note_change.type == ChangeTypes.CREATE:
        page_components = misli_gui.components_for_entity(
            note.page_id, Page)

        # Create a note component for all opened views for its page
        for pc in page_components:
            create_component_for_note(
                note.page_id, note.id, note.obj_class, pc.id)

            misli_gui.update_component(pc.id)

    elif note_change.type == ChangeTypes.UPDATE:
        note_components = misli_gui.components_for_entity(note.id, note.page_id)
        for nc in note_components:
            nc.set_props_from_entity(**note.state())

            # Hacky cache clearing
            nc.should_rebuild_pcommand_cache = True
            nc.should_reallocate_image_cache = True
            nc.should_rerender_image_cache = True

            misli_gui.update_component(nc.id)

    elif note_change.type == ChangeTypes.DELETE:
        note_components = misli_gui.components_for_entity(note.id)
        for nc in note_components:
            misli_gui.remove_component(nc.id)

        page_components = misli_gui.components_for_entity(
            note.page_id)

        for pc in page_components:
            misli_gui.update_component(pc.id)


@log.traced
def _update_components_for_page_change(page_change: Change):
    page_state = page_change.last_state()
    page = Page(**page_state)

    if page_change.type == ChangeTypes.CREATE:
        pass

    elif page_change.type == ChangeTypes.UPDATE:
        page_components = misli_gui.components_for_entity(page.id, Page)
        for pc in page_components:
            pc.set_props_from_entity(**page_state)
            misli_gui.update_component(pc.id)

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
