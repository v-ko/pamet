from datetime import datetime

import misli
from misli import entity_library
from misli.entity_library.change import Change
from misli.helpers import get_new_id, find_many_by_props, find_one_by_props
from misli import get_logger, Entity
from misli.gui import ENTITY_CHANGE_CHANNEL

from pamet.entities import Page, Note

log = get_logger(__name__)


_repo = None
_pages = {}
_note_indices = {}


# misli.add_channel(PAGES_CHANNEL)
# misli.add_channel(ENTITY_CHANGE_CHANNEL)

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
    # misli.add_channel(NOTES_CHANNEL(_page.id))


def remove_note_index_and_channel(page_id):
    del _note_indices[page_id]
    # misli.remove_channel(NOTES_CHANNEL(page_id))


@log.traced
def add_page(_page, _notes: list = None):
    _notes = _notes or []
    init_note_index_and_channel(_page, _notes)

    if not _page.id:
        _page.id = get_new_id()

    load_page(_page, _notes)
    change = Change.CREATE(state=_page)
    # misli.dispatch(change, PAGES_CHANNEL)
    misli.dispatch(change, ENTITY_CHANGE_CHANNEL)


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

    old_state = _page
    _page.replace(**page_state)
    _pages[_page.id] = _page

    change = Change.UPDATE(old_state, _page)
    # misli.dispatch(change, PAGES_CHANNEL)
    misli.dispatch(change, ENTITY_CHANGE_CHANNEL)


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

    _note = entity_library.from_dict(props)
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

    change = Change.CREATE(_note)
    misli.dispatch(change, ENTITY_CHANGE_CHANNEL)
    # misli.dispatch(change.asdict(), NOTES_CHANNEL(_note.page_id))


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

    change = Change.DELETE(_note)
    misli.dispatch(change, ENTITY_CHANGE_CHANNEL)
    # misli.dispatch(change.asdict(), NOTES_CHANNEL(_note.page_id))


@log.traced
def update_note(_note):
    if not _note.page_id or not _note.id:
        log.error('Could not update note without id and page_id set. '
                  'Note: %s' % _note)
        return

    old_note = note(_note.page_id, _note.id)

    if old_note.content != _note.content:
        _note.time_modified = datetime.now()

    _note_indices[_note.page_id][_note.id].replace(**_note.asdict())

    change = Change.UPDATE(old_note, _note)
    misli.dispatch(change, ENTITY_CHANGE_CHANNEL)
    # misli.dispatch(change.asdict(), NOTES_CHANNEL(_note.page_id))
