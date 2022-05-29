from __future__ import annotations

import misli
from misli import gui
from misli.basic_classes import Point2D
from misli.gui.actions_library import action

import pamet
from pamet.model import Note
from pamet.model.text_note import TextNote
from pamet.views.note.base_edit.view_state import NoteEditViewState
from pamet.views.tab import widget as tab_widget

log = misli.get_logger(__name__)


@action('notes.create_new_note')
def create_new_note(tab_state: tab_widget.TabViewState, new_note_pos: Point2D):
    # Check if there's an open edit window and abort it if so
    if tab_state.edit_view_state:
        abort_editing_note(tab_state)

    # Create the note
    page_view_state = tab_state.page_view_state
    position = page_view_state.unproject_point(new_note_pos)
    note: Note = TextNote(page_id=page_view_state.page.id)
    note.x = position.x()
    note.y = position.y()

    projected_center = page_view_state.project_point(
        note.rect().center())

    edit_view_state = NoteEditViewState(create_mode=True,
                                        # popup_position_center=projected_center,
                                        edited_note=note)
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

    position = tab_view_state.page_view_state.project_point(
        note.rect().center())

    edit_view_state = NoteEditViewState(create_mode=False,
                                        # popup_position_center=position,
                                        edited_note=note)
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
