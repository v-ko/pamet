import misli
from misli.core.primitives import Point
from misli.entities import Note
from misli.gui.actions_lib import action

log = misli.get_logger(__name__)


@action('notes.create_new_note')
def create_new_note(
        tab_component_id: str, position_coords: list, note_state: dict):

    tab_component = misli.gui.component(tab_component_id)
    position = Point.from_coords(position_coords)

    note = Note(**note_state)

    edit_component = misli.gui.create_component(
        'TextEdit', tab_component.id)

    edit_component.note = note
    edit_component.display_position = position
    edit_component.create_mode = True

    misli.gui.update_component(edit_component.id)


@action('notes.finish_creating_note')
def finish_creating_note(edit_component_id: str, note_state: dict):
    edit_component = misli.gui.component(edit_component_id)

    misli.create_note(**note_state)
    misli.gui.remove_component(edit_component.id)


@action('notes.start_editing_note')
def start_editing_note(
        tab_component_id: str, note_component_id: str, position_coords: list):

    note = misli.gui.entity_for_component(note_component_id)
    position = Point.from_coords(position_coords)

    edit_class_name = misli.gui.components_lib.get_edit_class_name(
        note.obj_class)
    edit_component = misli.gui.create_component_for_note(
        note.page_id, note.id, edit_class_name, tab_component_id)

    edit_component.note = note
    edit_component.display_position = position

    misli.gui.update_component(edit_component.id)


@action('notes.finish_editing_note')
def finish_editing_note(edit_component_id: str, note_state: dict):
    edit_component = misli.gui.component(edit_component_id)
    note = misli.gui.entity_for_component(edit_component_id)

    misli.update_note(**note_state)
    misli.update_page(note.page_id)

    misli.gui.remove_component(edit_component.id)

    # autosize_note(note_component_id)


@action('notes.abort_editing_note')
def abort_editing_note(edit_component_id: str):
    edit_component = misli.gui.component(edit_component_id)
    misli.gui.remove_component(edit_component.id)
