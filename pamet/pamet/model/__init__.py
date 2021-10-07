from datetime import datetime

import misli
from misli import entity_library
from misli import get_logger

from .page import Page  # So that they're accessible from the module
from .note import Note

log = get_logger(__name__)


# -------------Pages CRUD-------------
@log.traced
def pages():
    return misli.find(type_name='MapPage')


def page(page_id: str):
    return misli.find_one(gid=page_id)


@log.traced
def find_pages(**props):
    props['type_name'] = 'MapPage'
    return misli.find(**props)


@log.traced
def find_page(**props):
    props['type_name'] = 'MapPage'
    return misli.find_one(**props)


# -------------Notes CRUD-------------
def create_note(**props):
    if 'page_id' not in props:
        raise Exception('Cannot create note without passing a page_id kwarg')

    _note = entity_library.from_dict(props)
    _note.time_created = datetime.now()
    _note.time_modified = datetime.now()
    misli.insert(_note)
    return _note


# GUI helpers
@log.traced
def create_and_bind_page_view(page_id: str, parent_id: str):
    _page = page(page_id)
    page_view = misli.gui.create_view(
        parent_id,
        view_class_metadata_filter=dict(entity_type=_page.type_name),
        mapped_entity=_page)

    for _note in _page.notes():
        create_and_bind_note_view(page_view.id, _note)

    return page_view


@log.traced
def create_and_bind_note_view(page_view_id, _note):
    note_view = misli.gui.create_view(
        parent_id=page_view_id,
        view_class_metadata_filter=dict(entity_type=_note.type_name),
        mapped_entity=_note)

    return note_view


@log.traced
def create_and_bind_edit_view(tab_view_id, _note):
    edit_view = misli.gui.create_view(
        parent_id=tab_view_id,
        view_class_metadata_filter=dict(entity_type=_note.type_name, edit=True),
        mapped_entity=_note)

    return edit_view
