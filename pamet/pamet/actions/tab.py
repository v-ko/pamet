from __future__ import annotations
import misli
from misli.gui import action
from misli.basic_classes import Point2D

import pamet
from pamet.model.anchor_note import AnchorNote
from pamet.views.arrow.widget import ArrowViewState
from pamet.views.map_page.state import MapPageViewState
from pamet.model import Page
from pamet.helpers import generate_page_name
from pamet.actions import map_page as map_page_actions


@action('tab_go_to_page')
def tab_go_to_page(tab_state: TabViewState, page: Page):
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

    tab_state.page_view_state = page_view_state
    tab_state.title = page.name

    misli.gui.update_state(tab_state)
    misli.gui.update_state(page_view_state)


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
    new_page_link = AnchorNote(page_id=new_page.id)
    new_page_link.url = f'pamet:///p/{current_page.id}'
    new_page_link.x = note_position.x()
    new_page_link.y = note_position.y()
    pamet.insert_note(new_page_link)

    # Create a link to "old" page in the new one
    back_link_note = AnchorNote(page_id=current_page.id)
    back_link_note.url = f'pamet:///p/{new_page.id}'
    rect = back_link_note.rect()
    rect.move_center(Point2D(0, 0))
    back_link_note.set_rect(rect)
    pamet.insert_note(back_link_note)

    # Open the page and open its properties (with the name focused for editing)
    tab_go_to_page(tab_state, new_page)
    map_page_actions.open_page_properties(tab_state, focused_prop='name')


@action('tab.close_right_sidebar')
def close_right_sidebar(tab_state: TabViewState):
    # TODO: if tab_state.right_sidebar_state and unsaved shit: push notification
    tab_state.right_sidebar_visible = False
    tab_state.right_sidebar_state = None
    misli.gui.update_state(tab_state)
