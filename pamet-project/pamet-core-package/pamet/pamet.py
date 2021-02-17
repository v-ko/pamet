from typing import List

import misli
from misli.change import Change, ChangeTypes
from misli.helpers import get_new_id, find_many_by_props
from misli.helpers import find_one_by_props
import misli_gui

import pamet
from pamet.entities import Page, Note

from misli import get_logger
log = get_logger(__name__)

PAGES_CHANNEL = '__page_changes__'
ALL_NOTES_CHANNEL = '__all_notes_channel__'


def NOTES_CHANNEL(page_id):
    return '__notes_changes__%s' % page_id  # + page_id


_repo = None
_pages = {}
_note_indices = {}

binder = misli_gui.Binder()

misli.add_channel(PAGES_CHANNEL)
misli.add_channel(ALL_NOTES_CHANNEL)

# @log.traced
# def repo():
#     return _repo


# @log.traced
# def set_repo(repo, updates_channel: str):
#     global _repo
#     log.info('Setting repo to %s' % repo.path)

#     _repo = repo
#     misli.subscribe(repo.save_messages, updates_channel)


# -------------Pages CRUD-------------
def init_page(_page, _notes: list = None):
    _notes = _notes or []

    # Make a per-page notes index
    _note_indices[_page.id] = {}
    for n in _notes:
        _note_indices[_page.id][n.id] = n

    # For convenience make a per-page channel for notes updates
    misli.add_channel(NOTES_CHANNEL(_page.id))


def deinit_page(page_id):
    del _note_indices[page_id]
    misli.remove_channel(NOTES_CHANNEL(page_id))


@log.traced
def add_page(_page, _notes: list):
    init_page(_page, _notes)

    if not _page.id:
        _page.id = get_new_id()

    load_page(_page)
    change = Change(
        ChangeTypes.CREATE, old_state={}, new_state=_page.asdict())
    misli.dispatch(change.asdict(), PAGES_CHANNEL)


@log.traced
def load_page(_page: Page, notes: list):
    init_page(_page, notes)
    _pages[_page.id] = _page


@log.traced
def unload_page(page_id):
    deinit_page(page_id)
    del _pages[page_id]


@log.traced
def pages():
    return [page.copy() for pid, page in _pages.items()]


def page(page_id: str):
    return _pages[page_id].copy()


@log.traced
def find_pages(**props):
    return find_many_by_props(_pages, **props)


@log.traced
def find_page(**props):
    return find_one_by_props(_pages, **props)


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

    old_state = _page.asdict()
    _page.replace(**page_state)
    _pages[_page.id] = _page

    change = Change(ChangeTypes.UPDATE, old_state, _page.asdict())
    misli.dispatch(change.asdict(), PAGES_CHANNEL)


# @log.traced
# def delete_page(page_id: str):
#     _page = page(page_id)
#     if not _page:
#         log.error('Cannot unload missing page with id "%s"' % page_id)
#         return

#     unload_page(_page)
#     del _pages[_page.id]
#     change = Change(ChangeTypes.DELETE, _page.asdict(), {})
#     misli.dispatch(change.asdict(), PAGES_CHANNEL)


# -------------Notes CRUD-------------
# This is here (rather than in the Page class) because entities should be
# immutable and CRUD operations on notes via copied page objects would be
# ambiguous

def create_note(**props):
    if 'page_id' not in props:
        raise Exception('Cannot create note without passing a page_id kwarg')

    props['id'] = get_new_id()

    _note = Note(**props)
    add_note(_note)
    return _note


@log.traced
def add_note(_note):
    if not _note.id or not _note.page_id:
        raise Exception(
            'Cannot add note without an id or page_id. Note: %s' % _note)

    _page = page(_note.page_id)
    _note_indices[_page.id][_note.id] = _note

    change = Change(ChangeTypes.CREATE, {}, _note.asdict())
    misli.dispatch(change.asdict(), ALL_NOTES_CHANNEL)
    misli.dispatch(change.asdict(), NOTES_CHANNEL(_note.page_id))


def note(page_id: str, note_id: str):
    _page = page(page_id)
    if not _page:
        return None

    if note_id not in _note_indices[_page.id]:
        return None

    return _note_indices[_page.id][note_id].copy()


def notes(page_id):
    _page = page(page_id)
    return [note.copy() for nid, note in _note_indices[_page.id].items()]


@log.traced
def delete_note(_note: Note):
    if not note(_note.page_id, _note.id):
        raise Exception('Cannot remove missing note %s' % _note)

    del _note_indices[_note.page_id][_note.id]

    change = Change(ChangeTypes.DELETE, _note.asdict(), {})
    misli.dispatch(change.asdict(), ALL_NOTES_CHANNEL)
    misli.dispatch(change.asdict(), NOTES_CHANNEL(_note.page_id))


@log.traced
def update_note(_note):
    if not _note.page_id or not _note.id:
        log.error('Could not update note without id and page_id set. '
                  'Note: %s' % _note)
        return

    old_note = note(_note.page_id, _note.id)
    old_state = old_note.asdict()
    new_state = _note.asdict()
    _note_indices[_note.page_id][_note.id].replace(**new_state)

    change = Change(ChangeTypes.UPDATE, old_state, new_state)
    misli.dispatch(change.asdict(), ALL_NOTES_CHANNEL)
    misli.dispatch(change.asdict(), NOTES_CHANNEL(_note.page_id))


# @log.traced
# def delete_note(note_id):
#     _note = note(note_id)
#     if not _note:
#         raise Exception('Cannot delete missing note with id %s' % note_id)

#     del _note_indices[_note.page_id][_note.id]

#     change = Change(ChangeTypes.DELETE, _note.asdict(), {})
#     misli.dispatch(change.asdict(), ALL_NOTES_CHANNEL)
#     misli.dispatch(change.asdict(), NOTES_CHANNEL(_note.id))


# -------------------GUI stuff------------------------
@log.traced
def create_and_bind_page_component(page_id: str, parent_id: str):
    _page = page(page_id)
    page_component = misli_gui.create_component(
        obj_class=_page.obj_class, parent_id=parent_id)

    page_component_state = misli_gui.component_state(page_component.id)
    page_component_state.page = _page
    misli_gui.update_component_state(page_component_state)

    binder.map_component_to_entity(page_component, _page)

    for _note in notes(_page.id):
        create_and_bind_note_component(page_component.id, _note)

    return page_component


@log.traced
def create_and_bind_note_component(page_component_id, _note):
    note_component = misli_gui.create_component(
        obj_class=_note.obj_class, parent_id=page_component_id)

    note_component_state = misli_gui.component_state(note_component.id)
    note_component_state.note = _note
    misli_gui.update_component_state(note_component_state)

    binder.map_component_to_entity(note_component, _note)

    return note_component


@log.traced
def create_and_bind_edit_component(tab_component_id, _note):

    edit_class_name = misli_gui.components_lib.get_edit_class_name(
        _note.obj_class)

    edit_component = misli_gui.create_component(
        obj_class=edit_class_name, parent_id=tab_component_id)

    edit_component_state = misli_gui.component_state(edit_component.id)
    edit_component_state.note = _note
    misli_gui.update_component_state(edit_component_state)

    binder.map_component_to_entity(edit_component, _note)

    return edit_component


# I should consider refactoring those when I implement Changes (undo, etc)
# They might go into a reducer-like pattern (configured in main() ) but
# that should happen when needed and not earlier

@log.traced
def update_components_for_page_changes(changes: List[Change]):
    for page_change_dict in changes:
        page_change = Change(**page_change_dict)
        page_state = page_change.last_state()
        _page = Page(**page_state)

        if page_change.is_update():

            page_components = binder.components_mapped_to_entity(_page.gid())
            for pc in page_components:
                pcs = misli_gui.component_state(pc.id)
                pcs.page = _page
                misli_gui.update_component_state(pc.id)

        elif page_change.is_delete():
            page_components = binder.components_mapped_to_entity(_page.gid())
            for pc in page_components:
                misli_gui.remove_component(pc)
                # I may have to do something more elegant here - with
                # some kind of notification

        elif page_change.is_create():
            pass


@log.traced
def update_components_for_note_changes(changes: List[Change]):
    for note_change_dict in changes:
        note_change = Change(**note_change_dict)
        _note = Note(**note_change.last_state())

        if note_change.is_create():
            _page = pamet.page(_note.page_id)
            page_components = binder.components_mapped_to_entity(_page.gid())

            # Create a note component for all opened views for its page
            for pc in page_components:
                create_and_bind_note_component(pc.id, _note)

        elif note_change.is_update():
            note_components = binder.components_mapped_to_entity(_note.gid())

            for nc in note_components:
                ncs = misli_gui.component_state(nc.id)
                ncs.note = _note
                misli_gui.update_component_state(ncs)

        elif note_change.change_type == ChangeTypes.DELETE:
            note_components = binder.components_mapped_to_entity(_note.gid())
            for nc in note_components:
                misli_gui.remove_component(nc)


# @log.traced
# def update_components_from_changes(changes: List[Change]):
#     for change in changes:
#         obj_type = change.last_state()['obj_type']

#         if obj_type == 'Note':
#             _update_components_for_note_change(change)

#         elif obj_type == 'Page':
#             _update_components_for_page_change(change)

#         else:
#             raise NotImplementedError
