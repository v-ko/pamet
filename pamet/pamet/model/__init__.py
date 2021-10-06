from datetime import datetime
from collections import defaultdict

import misli
from misli import entity_library
from misli.entity_library.change import Change
from misli.helpers import get_new_id, find_many_by_props, find_one_by_props
from misli import get_logger

from .note import Note
from .page import Page

log = get_logger(__name__)


_pages = {}
_notes = {}
_notes_by_parent = defaultdict(list)
_changes = []


# -------------Pages CRUD-------------
@log.traced
def add_page(_page):
    if not _page.id:
        _page.id = get_new_id()

    misli.insert(_page)

# @log.traced
# def load_page(_page: Page, notes: list):
#     page_gid = _page.gid()
#     _pages[page_gid] = _page
#     for _note in notes:
#         _notes[_note.gid()] = _note
#         _notes_by_parent[page_gid] = _note


# @log.traced
# def unload_page(page_id):
#     for _note in page(page_id).notes():
#         del _notes[_note.gid()]
#     del _notes_by_parent[page(page_id).gid()]
#     del _pages[page_id]


@log.traced
def pages():
    return list(misli.find(obj_type='MapPage'))


def page(page_id: str):
    return misli.find_one(gid=page_id)


@log.traced
def find_pages(**props):
    props['obj_type'] = 'Page'
    return misli.find(**props)


@log.traced
def find_page(**props):
    props['obj_type'] = 'Page'
    return misli.find_one(**props)


# @log.traced
# def update_page(**page_state):

#     page_id = page_state.pop('id')
#     _page = page(page_id)
#     if not _page:
#         log.error('Cannot update missing page %s' % page_state['id'])
#         return

#     old_state = _page
#     _page.replace(**page_state)
#     _pages[_page.id] = _page

#     change = Change.UPDATE(old_state, _page)
#     # misli.dispatch(change, PAGES_CHANNEL)
#     misli.gui.broadcast_change(change)


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

    _note = entity_library.from_dict(props)
    _note.time_created = datetime.now()
    _note.time_modified = datetime.now()
    misli.insert(_note)
    return _note


@log.traced
def add_note(_note):
    if not _note.id or not _note.page_id:
        raise Exception(
            'Cannot add note without an id or page_id. Note: %s' % _note)

    misli.insert(_note)


def note(page_id: str, note_id: str):
    return misli.find_one(gid=(page_id, note_id))


def notes(page_id):
    _page = page(page_id)
    return misli.find(parent_gid=_page.gid())


@log.traced
def delete_note(_note: Note):
    misli.remove(_note)


@log.traced
def update_note(_note):
    old_note = note(_note.page_id, _note.id)

    if old_note.content != _note.content:
        _note.time_modified = datetime.now()

    misli.update(_note)
