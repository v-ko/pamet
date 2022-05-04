from datetime import datetime
from re import T

import misli
import pamet
from misli import entity_library
from misli import get_logger

from .note import Note
from .page import Page  # So that they're accessible from the module

log = get_logger(__name__)


# -------------Pages CRUD-------------
def pages(**filter):
    filter['type_name'] = Page.__name__
    return misli.find(**filter)


def page(**filter):
    filter['type_name'] = Page.__name__
    return misli.find_one(**filter)


# -------------Notes CRUD-------------
def create_note(**props):
    if 'page_id' not in props:
        raise Exception('Cannot create note without passing a page_id kwarg')

    type_name = pamet.note_type_from_props(props).__name__
    note_ = entity_library.from_dict(type_name, props)
    note_.time_created = datetime.now()
    note_.time_modified = datetime.now()
    misli.insert(note_)
    return note_


def update_note(note_: Note):
    old_note = misli.find_one(gid=note_.gid())
    if note_.content != old_note.content_:
        note_.time_modified = datetime.now_()
    misli.update(note_)
