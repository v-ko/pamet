from __future__ import annotations
import misli
from misli.gui import action
from misli.basic_classes import Point2D
from misli.logging import get_logger

import pamet
from pamet.constants import MAX_NAVIGATION_HISTORY
from pamet.model.text_note import TextNote
from pamet.views.arrow.widget import ArrowViewState
from pamet.views.map_page.state import MapPageViewState
from pamet.model import Page
from pamet.helpers import Url, generate_page_name
from pamet.actions import map_page as map_page_actions

log = get_logger(__name__)


@action('create_and_set_page')
def create_and_set_page_view(tab_state: TabViewState, url: str):
    parsed_url = Url(url)
    page = parsed_url.get_page()
    if not page:
        raise Exception('No page at the given URL')

    # Create the page state with all of its children states
    page_view_state = MapPageViewState(page_id=page.id)
    misli.gui.add_state(page_view_state)

    for _note in page.notes():
        NoteViewType = pamet.note_view_type(
            note_type_name=type(_note).__name__)
        StateType = pamet.note_state_type_by_view(NoteViewType.__name__)
        note_view_state = StateType(**_note.asdict(), note_gid=_note.gid())
        page_view_state.note_view_states.append(note_view_state)
        misli.gui.add_state(note_view_state)

    for arrow in page.arrows():
        arrow_view_state = ArrowViewState(**arrow.asdict(),
                                          arrow_gid=arrow.gid())
        page_view_state.arrow_view_states.append(arrow_view_state)
        misli.gui.add_state(arrow_view_state)
    misli.gui.update_state(page_view_state)

    # Set the page state in the tab state and handle the navigation history
    tab_state.page_view_state = page_view_state
    tab_state.title = page.name
    misli.gui.update_state(tab_state)


@action('go_to_url')
def go_to_url(tab_state: TabViewState, url: str):
    create_and_set_page_view(tab_state, url)

    # Add the url to the navigation history (only if it's different from
    # the last one)
    nav_history = tab_state.navigation_history
    if not nav_history or (nav_history and nav_history[-1] != url):
        nav_history.append(url)

    # Keep the nav history size in check
    if len(nav_history) > MAX_NAVIGATION_HISTORY:
        nav_history.pop(0)

    tab_state.set_navigation_index(len(nav_history) - 1)
    misli.gui.update_state(tab_state)


@action('page.create_and_link_page')
def create_new_page(tab_state: TabViewState, mouse_position: Point2D):
    # This action assumes there's a page opened
    current_page_state = tab_state.page_view_state
    current_page = current_page_state.page
    new_name = generate_page_name()
    new_page = Page(name=new_name)
    pamet.insert_page(new_page)

    # Create a link to the new page at the mouse position or center
    # (in the old one)
    note_position = current_page_state.unproject_point(mouse_position)
    new_page_link = TextNote(page_id=new_page.id)
    new_page_link.url = current_page.url()
    new_page_link.x = note_position.x()
    new_page_link.y = note_position.y()
    pamet.insert_note(new_page_link)

    # Create a link to "old" page in the new one
    back_link_note = TextNote(page_id=current_page.id)
    back_link_note.url = new_page.url()
    rect = back_link_note.rect()
    rect.move_center(Point2D(0, 0))
    back_link_note.set_rect(rect)
    pamet.insert_note(back_link_note)

    # Open the page and open its properties (with the name focused for editing)
    go_to_url(tab_state, new_page.url())
    map_page_actions.open_page_properties(tab_state, focused_prop='name')


@action('tab.close_right_sidebar')
def close_right_sidebar(tab_state: TabViewState):
    # TODO: if tab_state.right_sidebar_state and unsaved shit: push notification
    tab_state.right_sidebar_state = None
    misli.gui.update_state(tab_state)


@action('navigation_back')
def navigation_back(tab_state: TabViewState):
    nav_history = tab_state.navigation_history
    if not nav_history:
        log.error('Navigation back called with no navigation history present')
        return

    tab_state.set_navigation_index(tab_state.current_nav_index - 1)
    misli.gui.update_state(tab_state)
    create_and_set_page_view(tab_state,
                             nav_history[tab_state.current_nav_index])


@action('navigation_forward')
def navigation_forward(tab_state: TabViewState):
    nav_history = tab_state.navigation_history
    if not nav_history:
        log.error(
            'Navigation forward called with no navigation history present')
        return

    tab_state.set_navigation_index(tab_state.current_nav_index + 1)
    misli.gui.update_state(tab_state)
    create_and_set_page_view(tab_state,
                             nav_history[tab_state.current_nav_index])


@action('navigation_toggle_last')
def navigation_toggle_last(tab_state):
    if tab_state.previous_nav_index is None:
        return

    nav_history = tab_state.navigation_history
    tab_state.set_navigation_index(tab_state.previous_nav_index)
    misli.gui.update_state(tab_state)
    create_and_set_page_view(tab_state,
                             nav_history[tab_state.current_nav_index])
