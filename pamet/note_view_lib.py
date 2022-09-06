from __future__ import annotations
from fusion.libs.entity import Entity, get_entity_class_by_name

_view_types_by_note_type_name = {}
_edit_view_types_by_note_type_name = {}
_all_by_state_type_name = {}
_states_by_view_type_name = {}


def register_note_view_type(state_type, note_type, edit):
    state_type_name = state_type.__name__

    if not isinstance(note_type, (list, tuple)):
        note_type_names = [note_type.__name__]
    else:
        note_type_names = [nt.__name__ for nt in note_type]

    def view_registration_decorator(cls):
        if edit:
            for note_type_name in note_type_names:
                if note_type_name in _edit_view_types_by_note_type_name:
                    raise Exception('Class already registered (edit)')
                _edit_view_types_by_note_type_name[note_type_name] = cls
        else:
            for note_type_name in note_type_names:
                if note_type_name in _view_types_by_note_type_name:
                    raise Exception('Class already registered')
                _view_types_by_note_type_name[note_type_name] = cls

        _all_by_state_type_name[state_type_name] = cls
        _states_by_view_type_name[cls.__name__] = state_type
        return cls

    return view_registration_decorator


def note_view_type(note_type_name, edit=False) -> NoteViewState:
    if edit:
        return _edit_view_types_by_note_type_name[note_type_name]
    else:
        return _view_types_by_note_type_name[note_type_name]


def note_view_type_by_state(state_type_name):
    return _all_by_state_type_name[state_type_name]


def note_state_type_by_view(view_type_name):
    return _states_by_view_type_name[view_type_name]


def note_view_state_type_for_note(note, edit=False):
    NoteViewType = note_view_type(type(note).__name__, edit)
    return note_state_type_by_view(NoteViewType.__name__)


def note_types_with_assiciated_views() -> Entity:
    note_types = []
    for note_type_name in _view_types_by_note_type_name:
        note_type = get_entity_class_by_name(note_type_name)
        note_types.append(note_type)
    return note_types
