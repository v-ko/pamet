from __future__ import annotations
import fusion
from fusion.gui import action
from fusion.basic_classes import Point2D
from fusion.logging import get_logger

import pamet
from pamet.constants import MAX_NAVIGATION_HISTORY
from pamet.model.note import Note
from pamet.model.text_note import TextNote
from pamet.views.arrow.widget import ArrowViewState
from pamet.views.map_page.state import MapPageViewState
from pamet.model.page import Page
from pamet.helpers import generate_page_name
from pamet.url import Url
from pamet.actions import map_page as map_page_actions
from pamet.views.search_bar.widget import SearchBarWidgetState

log = get_logger(__name__)


@action('create_and_set_page')
def create_and_set_page_view(tab_state: TabViewState, url: str):
    parsed_url = Url(url)
    page = parsed_url.get_page()
    if not page:
        raise Exception('No page at the given URL')

    page_view_state = tab_state.page_state_from_cache(page.id)

    if not page_view_state:
        # Create the page state with all of its children states
        page_view_state = MapPageViewState(page_id=page.id)
        fusion.gui.add_state(page_view_state)

        for _note in pamet.notes(page):
            NoteViewType = pamet.note_view_type(
                note_type_name=type(_note).__name__)
            StateType = pamet.note_state_type_by_view(NoteViewType.__name__)
            note_props = _note.asdict()
            note_view_state = StateType(**note_props)
            page_view_state.note_view_states.add(note_view_state)
            fusion.gui.add_state(note_view_state)

        for arrow in pamet.arrows(page):
            arrow_props = arrow.asdict()
            arrow_view_state = ArrowViewState(**arrow_props)
            page_view_state.arrow_view_states.add(arrow_view_state)
            fusion.gui.add_state(arrow_view_state)
        fusion.gui.update_state(page_view_state)

    # Set the page state in the tab state (and cache it)
    tab_state.page_view_state = page_view_state
    tab_state.add_page_state_to_cache(page_view_state)
    tab_state.title = page.name
    fusion.gui.update_state(tab_state)


@action('go_to_url')
def go_to_url(tab_state: TabViewState,
              url: str,
              update_nav_history: bool = True):
    old_page_state = tab_state.page_view_state
    create_and_set_page_view(tab_state, url)

    parsed_url = Url(url)
    page_state = tab_state.page_view_state

    # Apply the anchor if any
    anchor = parsed_url.get_anchor()
    if anchor:
        height = page_state.viewport_height
        if isinstance(anchor, Note):
            center = anchor.rect().center()
        else:
            height, center = anchor

        page_state.viewport_height = height
        page_state.viewport_center = center
        fusion.gui.update_state(page_state)

    if not update_nav_history:
        return

    # Add the url to the navigation history
    nav_history = tab_state.navigation_history

    # If the page has changed
    last_page_id = None
    if nav_history:
        old_url = Url(nav_history[-1])
        last_page_id = old_url.page_id()

    if last_page_id != parsed_url.page_id():
        # Update the last url to save it's viewport position anchor
        # (to account for any viewport move/height changes
        # since the last go_to_url. This might have to be moved to the
        # finish_mouse_drag_move and height change actions)
        if old_page_state:
            nav_history[-1] = str(old_page_state.page_url())

        # Append the url to the nav history
        nav_history.append(str(page_state.page_url()))

    # Keep the nav history size in check
    if len(nav_history) > MAX_NAVIGATION_HISTORY:
        nav_history.pop(0)

    tab_state.set_navigation_index(len(nav_history) - 1)
    fusion.gui.update_state(tab_state)


@action('page.create_and_link_page')
def create_new_page(tab_state: TabViewState, mouse_position: Point2D):
    # This action assumes there's a page opened
    current_page_state = tab_state.page_view_state
    current_page = current_page_state.get_page()
    new_name = generate_page_name()
    new_page = Page(name=new_name)
    pamet.insert_page(new_page)

    # Create a link to the new page at the mouse position or center
    # (in the old one)
    note_position = current_page_state.unproject_point(mouse_position)
    new_page_link = TextNote.in_page(new_page)
    new_page_link.url = current_page.url()
    new_page_link.x = note_position.x()
    new_page_link.y = note_position.y()
    pamet.insert_note(new_page_link)

    # Create a link to "old" page in the new one
    back_link_note = TextNote.in_page(current_page)
    back_link_note.url = new_page.url()
    rect = back_link_note.rect()
    rect.move_center(Point2D(0, 0))
    back_link_note.set_rect(rect)
    pamet.insert_note(back_link_note)

    # Open the page and open its properties (with the name focused for editing)
    go_to_url(tab_state, new_page.url())
    map_page_actions.open_page_properties(tab_state, focused_prop='name')


@action('navigation_back')
def navigation_back(tab_state: TabViewState):
    nav_history = tab_state.navigation_history
    if not nav_history:
        log.error('Navigation back called with no navigation history present')
        return

    tab_state.set_navigation_index(tab_state.current_nav_index - 1)
    fusion.gui.update_state(tab_state)
    go_to_url(tab_state,
              nav_history[tab_state.current_nav_index],
              update_nav_history=False)


@action('navigation_forward')
def navigation_forward(tab_state: TabViewState):
    nav_history = tab_state.navigation_history
    if not nav_history:
        log.error(
            'Navigation forward called with no navigation history present')
        return

    tab_state.set_navigation_index(tab_state.current_nav_index + 1)
    fusion.gui.update_state(tab_state)
    go_to_url(tab_state,
              nav_history[tab_state.current_nav_index],
              update_nav_history=False)


@action('navigation_toggle_last')
def navigation_toggle_last(tab_state):
    if tab_state.previous_nav_index is None:
        return

    nav_history = tab_state.navigation_history
    tab_state.set_navigation_index(tab_state.previous_nav_index)
    fusion.gui.update_state(tab_state)
    go_to_url(tab_state,
              nav_history[tab_state.current_nav_index],
              update_nav_history=False)


@action('tab.close_right_sidebar')
def close_right_sidebar(tab_state: TabViewState):
    # TODO: if tab_state.right_sidebar_state and unsaved shit: push notification
    tab_state.right_sidebar_state = None
    fusion.gui.update_state(tab_state)


@action('tab.open_global_search')
def open_global_search(tab_state: TabViewState):
    # If not present - create the search bar state
    if not tab_state.search_bar_state:
        tab_state.search_bar_state = SearchBarWidgetState()
        fusion.gui.add_state(tab_state.search_bar_state)

    tab_state.left_sidebar_state = tab_state.search_bar_state
    fusion.gui.update_state(tab_state)


@action('tab.close_left_sidebar')
def close_left_sidebar(tab_state: TabViewState):
    tab_state.left_sidebar_state = None
    fusion.gui.update_state(tab_state)
