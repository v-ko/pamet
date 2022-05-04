from __future__ import annotations
from os import stat

from misli.gui.view_library import view
from pamet.model.text_note import TextNote
from .model import page, pages, create_note

# from misli.gui import KeyBinding
from pamet.views.note.base_note_view import NoteViewState

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
    # for state_type_name_, view_type in _all_by_state_type_name.items():
    #     if state_type_name == state_type_name_:
    #         return view_type

    # raise Exception('No view type with this name')


def note_state_type_by_view(view_type_name):
    return _states_by_view_type_name[view_type_name]


def note_type_from_props(props):
    # I can infer the note type by doing kind of an IOU for the fields.
    # I.e. iterate over the note types and sort them by match
    return TextNote  # Mock/ testing
