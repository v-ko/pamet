from __future__ import annotations

from pathlib import Path
from typing import Union
from urllib.parse import ParseResult, urlparse

from misli.entity_library import get_entity_class_by_name

# from misli.gui.view_library import view
from .model import page, pages, create_note, set_sync_repo, set_async_repo
from .model import find, find_one, insert_note, insert_page, update_note
from .model import update_page, remove_note, remove_page
from .model import insert_arrow, remove_arrow, update_arrow
from pamet.model.text_note import TextNote

from misli import get_logger

log = get_logger(__name__)
# from misli.gui import KeyBinding
# from pamet.views.note.base_note_view import NoteViewState

default_key_bindings = [
    # KeyBinding('N', commands.create_new_note, conditions='pageFocus'),
    # KeyBinding('Ctrl+N', commands.create_new_page, conditions='pageFocus'),
    # KeyBinding('Ctrl+S',
    #            commands.save_page_properties,
    #            conditions='inPageProperties'),
    # KeyBinding('E', commands.edit_selected_notes, conditions='notesSelected')
]


def configure_for_qt():
    # Force view registration
    from pamet.views.map_page.widget import MapPageWidget
    from pamet.views.note.text.widget import TextNoteWidget
    from pamet.views.note.text.edit_widget import TextNoteEditWidget
    from pamet.views.note.anchor.widget import AnchorWidget
    from pamet.views.note.anchor.edit_widget import AnchorEditWidget


_view_types = {}
_edit_view_types = {}
_all_by_state_type_name = {}
_states_by_view_type_name = {}


def register_note_view_type(state_type, note_type, edit):
    state_type_name = state_type.__name__
    note_type_name = note_type.__name__

    def view_registration_decorator(cls):
        if edit:
            if note_type_name in _edit_view_types:
                raise Exception('Class already registered (edit)')
            _edit_view_types[note_type_name] = cls
        else:
            if note_type_name in _view_types:
                raise Exception('Class already registered')
            _view_types[note_type_name] = cls

        _all_by_state_type_name[state_type_name] = cls
        _states_by_view_type_name[cls.__name__] = state_type
        return cls

    return view_registration_decorator


def note_view_type(note_type_name, edit=False) -> NoteViewState:
    if edit:
        return _edit_view_types[note_type_name]
    else:
        return _view_types[note_type_name]


def note_view_type_by_state(state_type_name):
    return _all_by_state_type_name[state_type_name]


def note_state_type_by_view(view_type_name):
    return _states_by_view_type_name[view_type_name]


def note_view_state_type_for_note(note, edit=False):
    NoteViewType = note_view_type(type(note).__name__, edit)
    return note_state_type_by_view(NoteViewType.__name__)


def note_type_from_props(props):
    # I can infer the note type by doing kind of an IOU for the fields.
    # I.e. iterate over the note types and sort them by match
    try:
        note_type = get_entity_class_by_name(props['type_name'])  #@IgnoreException
    except Exception:
        return None

    return note_type

def resource_path(subpath: Union[str, Path]):
    resource_dir_path = Path(__file__).parent / 'resources'
    resource_path = resource_dir_path / Path(subpath)

    if subpath.startswith('/'):
        subpath = subpath[1:]

    if not resource_path.exists():
        raise Exception('Resource not found')
    return resource_path
