import misli
from misli import gui, Entity
from misli.basic_classes import Point2D
from misli.gui.actions_lib import action

import pamet
from pamet.entities import Note


log = misli.get_logger(__name__)


@action('notes.create_new_note')
def create_new_note(
        tab_view_id: str, position_coords: list, note_state: dict):

    position = Point2D.from_coords(position_coords)
    note = Entity.from_dict(note_state)

    # Check if there's an open edit window and abort it if so
    tab_state = gui.view_model(tab_view_id)
    if tab_state.edit_view_id:
        abort_editing_note(tab_state.edit_view_id)

    edit_view_class = gui.view_library.get_view_class(
        obj_type='TextNote', edit=True)
    edit_view = edit_view_class(parent_id=tab_view_id)
    tab_state.edit_view_id = edit_view.id

    edit_view_model = gui.view_model(edit_view.id)
    edit_view_model.note = note
    edit_view_model.display_position = position
    edit_view_model.create_mode = True

    gui.update_view_model(edit_view_model)
    gui.update_view_model(tab_state)


@action('notes.finish_creating_note')
def finish_creating_note(edit_view_id: str, note: Note):
    edit_view = gui.view(edit_view_id)

    pamet.create_note(**note.asdict())
    gui.remove_view(edit_view)


@action('notes.start_editing_note')
def start_editing_note(
        tab_view_id: str, note_component_id: str, position_coords: list):

    note = gui.view(note_component_id).note
    position = Point2D.from_coords(position_coords)

    # Check if there's an open edit window and abort it if so
    tab_state = gui.view_model(tab_view_id)
    if tab_state.edit_view_id:
        abort_editing_note(tab_state.edit_view_id)

    edit_view = pamet.create_and_bind_edit_view(tab_view_id, note)
    tab_state.edit_view_id = edit_view.id
    edit_view_model = gui.view_model(edit_view.id)
    edit_view_model.display_position = position

    gui.update_view_model(edit_view_model)
    gui.update_view_model(tab_state)


@action('notes.finish_editing_note')
def finish_editing_note(edit_view_id: str, note: Note):
    edit_view = gui.view(edit_view_id)

    pamet.update_note(note)
    gui.remove_view(edit_view)

    # autosize_note(note_component_id)


@action('notes.abort_editing_note')
def abort_editing_note(edit_view_id: str):
    edit_view = gui.view(edit_view_id)
    tab_state = gui.view_model(edit_view.parent_id)
    tab_state.edit_view_id = None

    gui.remove_view(edit_view)
    gui.update_view_model(tab_state)
