from __future__ import annotations

import misli
from misli import gui
from misli.basic_classes import Point2D
from misli.gui.actions_library import action

import pamet
from pamet.model import Note
from pamet.model.text_note import TextNote
from pamet.views.note.text.edit_view import TextNoteEditViewState
from pamet.views.tab import widget as tab_widget

log = misli.get_logger(__name__)


@action('notes.create_new_note')
def create_new_note(tab_state: tab_widget.TabViewState, new_note_pos: Point2D):
    # Check if there's an open edit window and abort it if so
    if tab_state.edit_view_state:
        abort_editing_note(tab_state)

    # Create the note
    page_view_state = tab_state.page_view_state
    position = page_view_state.viewport.unproject_point(new_note_pos)
    note = TextNote(page_id=page_view_state.page.id)
    note.x = position.x()
    note.y = position.y()

    edit_view_state = TextNoteEditViewState(create_mode=True,
                                            display_position=new_note_pos,
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

    position = tab_view_state.page_view_state.viewport.project_point(
        note.rect().center())

    edit_view_state = TextNoteEditViewState(create_mode=False,
                                            display_position=position,
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
