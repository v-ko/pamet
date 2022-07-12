from typing import Tuple

import misli
from misli.gui import command

from pamet import actions
from pamet.actions import note as note_actions
from pamet.actions import map_page as map_page_actions
from pamet.actions import window as window_actions

from pamet.gui_helpers import current_window, current_tab
from pamet.views.note.base_note_view import NoteViewState

log = misli.get_logger(__name__)


def current_tab_and_page_views() -> Tuple:
    tab = current_tab()
    if not tab:
        raise Exception('There\'s no open tab.')

    page_view = tab.page_view()
    if not page_view:
        raise Exception('No page view.')

    return tab, page_view


@command(title='Create new note')
def create_new_note():
    current_window().current_tab().create_new_note_command()


@command(title='Create new page')
def create_new_page():
    current_window().current_tab().create_new_page_command()


@command(title='Save page properties')
def save_page_properties():
    tab, page_view = current_tab_and_page_views()
    properties_view_state = misli.gui.view_state(
        tab.state().right_sidebar_view_id)
    page = properties_view_state.page
    page.name = properties_view_state.name_line_edit_text
    map_page_actions.save_page_properties(page)
    map_page_actions.close_page_properties(properties_view_state.id)


@command(title='Open page properties')
def open_page_properties():
    tab, page_view = current_tab_and_page_views()
    map_page_actions.open_page_properties(tab.state())


@command(title='Edit selected note')
def edit_selected_notes():
    tab, page_view = current_tab_and_page_views()
    selected_child_ids = page_view.state().selected_child_ids
    if not selected_child_ids:
        return

    for note_view_id in selected_child_ids:
        note_state = misli.gui.view_state(note_view_id)
        if not isinstance(note_state, NoteViewState):
            continue
        note_actions.start_editing_note(tab.state(), note_state.get_note())


@command(title='Show all commands')
def open_command_palette():
    window_actions.open_command_view(current_window().state(),
                                     prefix='>')


@command(title='Go to file')
def open_command_palette_go_to_file():
    window_actions.open_command_view(current_window().state())


@command(title='Create an arrow')
def start_arrow_creation():
    tab, page_view = current_tab_and_page_views()

    map_page_actions.start_arrow_creation(page_view.state())


@command(title='Resize selected notes to fit text')
def autosize_selected_notes():
    tab, page_view = current_tab_and_page_views()

    page_view.autosize_selected_notes()
