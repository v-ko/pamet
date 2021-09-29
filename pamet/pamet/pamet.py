from typing import List
from datetime import datetime

import misli
from misli.change import Change, ChangeTypes
from misli.helpers import get_new_id, find_many_by_props, find_one_by_props
from misli import get_logger, gui, Entity

import pamet
from pamet.entities import Page, Note

log = get_logger(__name__)

PAGES_CHANNEL = '__page_changes__'
ALL_NOTES_CHANNEL = '__all_notes_channel__'


def NOTES_CHANNEL(page_id):
    return '__notes_changes__%s' % page_id


_repo = None
_pages = {}
_note_indices = {}

binder = gui.EntityToViewMapping()

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
def init_note_index_and_channel(_page, _notes: list = None):
    _notes = _notes or []

    # Make a per-page notes index
    _note_indices[_page.id] = {}
    for n in _notes:
        _note_indices[_page.id][n.id] = n

    # For convenience make a per-page channel for notes updates
    misli.add_channel(NOTES_CHANNEL(_page.id))


def remove_note_index_and_channel(page_id):
    del _note_indices[page_id]
    misli.remove_channel(NOTES_CHANNEL(page_id))


@log.traced
def add_page(_page, _notes: list = None):
    _notes = _notes or []
    init_note_index_and_channel(_page, _notes)

    if not _page.id:
        _page.id = get_new_id()

    load_page(_page, _notes)
    change = Change(
        ChangeTypes.CREATE, old_state={}, new_state=_page.asdict())
    misli.dispatch(change.asdict(), PAGES_CHANNEL)


@log.traced
def load_page(_page: Page, notes: list):
    init_note_index_and_channel(_page, notes)
    _pages[_page.id] = _page


@log.traced
def unload_page(page_id):
    remove_note_index_and_channel(page_id)
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

    _note = Entity.from_dict(props)
    _note.time_created = datetime.now()
    _note.time_modified = datetime.now()
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

    if old_note.content != _note.content:
        _note.time_modified = datetime.now()

    old_state = old_note.asdict()
    new_state = _note.asdict()

    _note_indices[_note.page_id][_note.id].replace(**new_state)

    change = Change(ChangeTypes.UPDATE, old_state, new_state)
    misli.dispatch(change.asdict(), ALL_NOTES_CHANNEL)
    misli.dispatch(change.asdict(), NOTES_CHANNEL(_note.page_id))


# -------------------GUI stuff------------------------
@log.traced
def create_and_bind_page_view(page_id: str, parent_id: str):
    _page = page(page_id)

    page_view_class = misli.gui.view_library.get_view_class(
        obj_type=_page.obj_type)
    page_view = page_view_class(parent_id=parent_id)

    page_view_state = gui.view_state(page_view.id)
    page_view_state.page = _page
    gui.update_state(page_view_state)

    binder.map_entity_to_view(_page.gid(), page_view.id)

    for _note in notes(_page.id):
        create_and_bind_note_view(page_view.id, _note)

    return page_view


@log.traced
def create_and_bind_note_view(page_view_id, _note):
    note_view_class = misli.gui.view_library.get_view_class(
        obj_type=_note.obj_type, edit=False)
    note_view = note_view_class(parent_id=page_view_id)

    note_view_state = gui.view_state(note_view.id)
    note_view_state.note = _note
    gui.update_state(note_view_state)

    binder.map_entity_to_view(_note.gid(), note_view.id)
    return note_view


@log.traced
def create_and_bind_edit_view(tab_view_id, _note):
    edit_class = misli.gui.view_library.get_view_class(
        obj_type=_note.obj_type, edit=True)
    edit_view = edit_class(parent_id=tab_view_id)

    edit_view_state = gui.view_state(edit_view.id)
    edit_view_state.note = _note
    gui.update_state(edit_view_state)

    binder.map_entity_to_view(_note.gid(), edit_view.id)

    return edit_view


# I should consider refactoring those when I implement Changes (undo, etc)
# They might go into a reducer-like pattern (configured in main() ) but
# that should happen when needed and not earlier

@gui.action('update_views_for_page_changes')
def update_views_for_page_changes(changes: List[dict]):
    for page_change_dict in changes:
        page_change = Change(**page_change_dict)
        page_state = page_change.last_state()
        _page = Entity.from_dict(page_state)

        if page_change.is_update():

            page_views = binder.views_mapped_to_entity(_page.gid())
            for pc in page_views:
                pcs = gui.view_state(pc.id)
                pcs.page = _page
                gui.update_state(pc.id)

        elif page_change.is_delete():
            page_views = binder.views_mapped_to_entity(_page.gid())
            for pc in page_views:
                gui.remove_view(pc)
                # I may have to do something more elegant here - with
                # some kind of notification

        elif page_change.is_create():
            pass


@gui.action('update_views_for_note_changes')
def update_views_for_note_changes(changes: List[dict]):
    for note_change_dict in changes:
        note_change = Change(**note_change_dict)
        _note = Entity.from_dict(note_change.last_state())

        if note_change.is_create():
            _page = pamet.page(_note.page_id)
            page_views = binder.views_mapped_to_entity(_page.gid())

            # Create a note component for all opened views for its page
            for pc in page_views:
                create_and_bind_note_view(pc.id, _note)

        elif note_change.is_update():
            note_views = binder.views_mapped_to_entity(_note.gid())

            for nc in note_views:
                ncs = gui.view_state(nc.id)
                ncs.note = _note
                gui.update_state(ncs)

        elif note_change.type == ChangeTypes.DELETE:
            note_views = binder.views_mapped_to_entity(_note.gid())
            for nc in note_views:
                gui.remove_view(nc)
