import misli
import misli_gui
import pamet
from misli.basic_classes import Point
from pamet.entities import Note
from misli_gui.actions_lib import action

log = misli.get_logger(__name__)


@action('notes.create_new_note')
def create_new_note(
        tab_component_id: str, position_coords: list, note_state: dict):

    tab_component = misli_gui.component(tab_component_id)
    position = Point.from_coords(position_coords)

    note = Note(**note_state)

    edit_component = misli_gui.create_component(
        'TextEdit', tab_component.id)
    edit_component_state = misli_gui.component_state(edit_component.id)

    edit_component_state.note = note
    edit_component_state.display_position = position
    edit_component_state.create_mode = True

    misli_gui.update_component_state(edit_component_state)


@action('notes.finish_creating_note')
def finish_creating_note(edit_component_id: str, note: Note):
    edit_component = misli_gui.component(edit_component_id)

    pamet.create_note(**note.asdict())
    misli_gui.remove_component(edit_component)


@action('notes.start_editing_note')
def start_editing_note(
        tab_component_id: str, note_component_id: str, position_coords: list):

    note = misli_gui.component(note_component_id).note
    position = Point.from_coords(position_coords)

    edit_component = pamet.create_and_bind_edit_component(
        tab_component_id, note)

    # edit_component.note = note
    edit_component_state = misli_gui.component_state(edit_component.id)
    edit_component_state.display_position = position

    misli_gui.update_component_state(edit_component_state)


@action('notes.finish_editing_note')
def finish_editing_note(edit_component_id: str, note: Note):
    edit_component = misli_gui.component(edit_component_id)

    pamet.update_note(note)
    misli_gui.remove_component(edit_component)

    # autosize_note(note_component_id)


@action('notes.abort_editing_note')
def abort_editing_note(edit_component_id: str):
    edit_component = misli_gui.component(edit_component_id)
    misli_gui.remove_component(edit_component)
