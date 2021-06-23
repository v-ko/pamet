import misli
from misli import gui
import pamet
from misli.basic_classes import Point
from pamet.entities import Note
from misli.gui.actions_lib import action

log = misli.get_logger(__name__)


@action('notes.create_new_note')
def create_new_note(
        tab_view_id: str, position_coords: list, note_state: dict):

    position = Point.from_coords(position_coords)
    note = Note.from_dict(note_state)

    # edit_view = gui.create_view(
    #     'TextEdit', tab_view.id)
    edit_view_class = pamet.view_library.get_edit_view_class('Text')
    edit_view = edit_view_class(parent_id=tab_view_id)

    edit_view_model = gui.view_model(edit_view.id)
    edit_view_model.note = note
    edit_view_model.display_position = position
    edit_view_model.create_mode = True

    gui.update_view_model(edit_view_model)


@action('notes.finish_creating_note')
def finish_creating_note(edit_view_id: str, note: Note):
    edit_view = gui.view(edit_view_id)

    pamet.create_note(**note.asdict())
    gui.remove_view(edit_view)


@action('notes.start_editing_note')
def start_editing_note(
        tab_view_id: str, note_component_id: str, position_coords: list):

    note = gui.view(note_component_id).note
    position = Point.from_coords(position_coords)

    edit_view = pamet.create_and_bind_edit_view(
        tab_view_id, note)

    edit_view_model = gui.view_model(edit_view.id)
    edit_view_model.display_position = position

    gui.update_view_model(edit_view_model)


@action('notes.finish_editing_note')
def finish_editing_note(edit_view_id: str, note: Note):
    edit_view = gui.view(edit_view_id)

    pamet.update_note(note)
    gui.remove_view(edit_view)

    # autosize_note(note_component_id)


@action('notes.abort_editing_note')
def abort_editing_note(edit_view_id: str):
    edit_view = gui.view(edit_view_id)
    gui.remove_view(edit_view)
