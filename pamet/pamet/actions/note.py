from __future__ import annotations

import misli
from misli import gui
from misli.gui.actions_library import action

import pamet
from pamet.model import Note
from pamet.views.note.anchor.widget import AnchorViewState
from pamet.views.tab import widget as tab_widget

log = misli.get_logger(__name__)


@action('notes.create_new_note')
def create_new_note(tab_state: tab_widget.TabViewState,
                    note: Note):
    # Check if there's an open edit window and abort it if so
    if tab_state.edit_view_state:
        abort_editing_note(tab_state)

    EditViewType = pamet.note_view_state_type_for_note(note, edit=True)
    edit_view_state = EditViewType(
        note_gid=note.gid(),
        new_note_dict=note.asdict())
    edit_view_state.update_from_note(note)

    tab_state.edit_view_state = edit_view_state

    gui.add_state(edit_view_state)
    gui.update_state(tab_state)


@action('notes.finish_creating_note')
def finish_creating_note(tab_state: tab_widget.TabViewState, note: Note):
    pamet.create_note(**note.asdict())
    tab_state.edit_view_state = None
    gui.update_state(tab_state)


@action('notes.start_editing_note')
def start_editing_note(tab_view_state: tab_widget.TabViewState, note: Note):
    # Check if there's an open edit window and abort it if so
    if tab_view_state.edit_view_state:
        abort_editing_note(tab_view_state)

    EditViewType = pamet.note_view_state_type_for_note(note, edit=True)
    edit_view_state = EditViewType(
        note_gid=note.gid())
    edit_view_state.update_from_note(note)
    tab_view_state.edit_view_state = edit_view_state

    gui.add_state(edit_view_state)
    gui.update_state(tab_view_state)


@action('notes.finish_editing_note')
def finish_editing_note(tab_state: tab_widget.TabViewState, note: Note):
    pamet.update_note(note)
    gui.remove_state(tab_state.edit_view_state)
    tab_state.edit_view_state = None
    gui.update_state(tab_state)
    # autosize_note(note_component_id)


@action('notes.abort_editing_note')
def abort_editing_note(tab_state: tab_widget.TabViewState):
    tab_state.edit_view_state = None
    gui.update_state(tab_state)


@action('note.apply_page_change_to_anchor_view')
def apply_page_change_to_anchor_view(anchor_view_state: AnchorViewState):
    anchor_view_state.update_link_validity()
    misli.gui.update_state(anchor_view_state)
