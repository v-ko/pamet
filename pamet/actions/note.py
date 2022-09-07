from __future__ import annotations

import fusion
from fusion.libs.entity import dump_to_dict
from fusion.util import current_time
import pamet.views.tab.state
from fusion import fsm
from fusion.libs.action import action

import pamet
from pamet.util import snap_to_grid
from pamet.model.note import Note
from pamet.views.note.qt_helpers import minimal_nonelided_size
from pamet.actions import map_page as map_page_actions

log = fusion.get_logger(__name__)


@action('notes.create_new_note')
def create_new_note(tab_state: TabViewState, note: Note):
    # Check if there's an open edit window and abort it if so
    if tab_state.note_edit_view_state:
        abort_editing_note(tab_state)

    EditViewType = pamet.note_view_state_type_for_note(note, edit=True)
    edit_view_state = EditViewType(id=note.gid(),
                                   new_note_dict=dump_to_dict(note))
    edit_view_state.update_from_note(note)

    tab_state.note_edit_view_state = edit_view_state

    fsm.add_state(edit_view_state)
    fsm.update_state(tab_state)


@action('notes.finish_creating_note')
def finish_creating_note(tab_state: TabViewState, note: Note):
    # note = pamet.create_note(**note.asdict())

    note.datetime_created = current_time()
    note.datetime_modified = current_time()

    # Autosize the note
    rect = note.rect()
    rect.set_size(snap_to_grid(minimal_nonelided_size(note)))
    note.set_rect(rect)
    pamet.insert_note(note)

    tab_state.note_edit_view_state = None
    fsm.update_state(tab_state)


@action('notes.start_editing_note')
def start_editing_note(tab_view_state: TabViewState, note: Note):
    # Check if there's an open edit window and abort it if so
    if tab_view_state.note_edit_view_state:
        abort_editing_note(tab_view_state)

    EditViewType = pamet.note_view_state_type_for_note(note, edit=True)
    edit_view_state = EditViewType(id=note.gid())
    edit_view_state.update_from_note(note)
    tab_view_state.note_edit_view_state = edit_view_state

    fsm.add_state(edit_view_state)
    fsm.update_state(tab_view_state)


@action('notes.finish_editing_note')
def finish_editing_note(tab_state: TabViewState, note: Note):
    pamet.update_note(note)
    fsm.remove_state(tab_state.note_edit_view_state)
    tab_state.note_edit_view_state = None
    fsm.update_state(tab_state)
    # autosize_note(note_component_id)


@action('notes.abort_editing_note')
def abort_editing_note(tab_state: TabViewState):
    tab_state.note_edit_view_state = None
    fsm.update_state(tab_state)


@action('notes.abort_editing_and_delete_note')
def abort_editing_and_delete_note(tab_state: TabViewState):
    note = tab_state.note_edit_view_state.get_note()
    map_page_actions.delete_notes_and_connected_arrows([note])
    abort_editing_note(tab_state)


@action('note.apply_page_change_to_anchor_view')
def apply_page_change_to_anchor_view(
        note_view_state: tab_widget.TextNoteViewState):
    page = pamet.page(note_view_state.url.get_page_id())
    # If it's missing - leave the text, the border will indicate
    if page:
        note_view_state.text = page.name
    else:
        note_view_state.text += '(removed)'
    fsm.update_state(note_view_state)


@action('note.switch_note_type')
def switch_note_type(tab_state: TabViewState, note: Note):
    if tab_state.note_edit_view_state.create_mode:
        abort_editing_note(tab_state)
        create_new_note(tab_state, note)
    else:
        finish_editing_note(tab_state, note)
        start_editing_note(tab_state, note)
