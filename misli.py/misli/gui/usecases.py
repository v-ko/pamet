import misli
from misli.core.primitives import Point
from misli.objects import Note
from misli.gui.actions_lib import action

log = misli.get_logger(__name__)


@action('notes.create_new_note')
def create_new_note(tab_component_id: int, position_coords, **note_state):
    log.info('create_new_note', extra=note_state)
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
def finish_creating_note(edit_component_id, **note_state):
    log.info('finish_creating_note', extra=note_state)

    edit_component = misli.gui.component(edit_component_id)
    note = edit_component.note

    misli.create_note(**note.state())
    misli.gui.remove_component(edit_component.id)


@action('notes.start_editing_note')
def start_editing_note(tab_component_id, note_component_id, position_coords):
    log.info(
        'start_editing_note')

    note = misli.gui.base_object_for_component(note_component_id)
    position = Point.from_coords(position_coords)

    edit_class_name = misli.gui.components_lib.get_edit_class_name(
        note.obj_class)
    edit_component = misli.gui.create_component_for_note(
        note.page_id, note.id, edit_class_name, tab_component_id)

    edit_component.note = note
    edit_component.display_position = position

    misli.gui.update_component(edit_component.id)


@action('notes.finish_editing_note')
def finish_editing_note(edit_component_id, **note_state):
    log.info('finish_editing_note', extra=note_state)

    edit_component = misli.gui.component(edit_component_id)
    note = misli.gui.base_object_for_component(edit_component_id)

    misli.update_note(**note_state)
    misli.update_page(note.page_id)

    misli.gui.remove_component(edit_component.id)


@action('notes.abort_editing_note')
def abort_editing_note(edit_component_id):
    log.info('abort_editing_note')

    edit_component = misli.gui.component(edit_component_id)
    misli.gui.remove_component(edit_component.id)
