import misli
from misli.gui import action
from misli.basic_classes import Point2D

import pamet
from pamet.views.tab.view import BrowserTabView
from pamet.model import Page
from pamet.model.text_note import TextNote
from pamet.helpers import generate_default_page_id


@action('tab_go_to_page')
def tab_go_to_page(tab_component_id, page_id):
    page = pamet.page(gid=page_id)
    page_view = pamet.create_and_bind_page_view(
        page.id, parent_id=tab_component_id)

    page_view_state = misli.gui.view_state(page_view.id)
    page_view_state.page = page

    tab_view_state = misli.gui.view_state(tab_component_id)
    tab_view_state.page_view_id = page_view.id
    tab_view_state.name = page.name

    misli.gui.update_state(tab_view_state)
    misli.gui.update_state(page_view_state)


@action('tab_go_to_default_page')
def tab_go_to_default_page(tab_component_id):
    pass


@action('page.create_and_link_page')
def create_new_page(tab_view_id: str, mouse_position: Point2D):
    tab: BrowserTabView = misli.gui.view(tab_view_id)
    parent_page = tab.page_view().page

    new_page = Page(id=generate_default_page_id())
    misli.insert(new_page)

    # Create a link to the new page at the mouse position or center
    # (in the old one)
    page_view = tab.page_view()
    note_position = page_view.viewport.project_point(mouse_position)
    # TODO: finish this
    link_note = TextNote(parent_id=page_view.page.id, text='Mock link')
    link_note.x = note_position.x()
    link_note.y = note_position.y()
    misli.insert(link_note)

    # Create a link to "old" page in the new one
    back_link_note = TextNote(parent_id=new_page.id, text='Mock backlink')
    rect = back_link_note.rect()
    rect.move_center(Point2D(0, 0))
    back_link_note.set_rect(rect)
    misli.insert(back_link_note)

    tab_go_to_page(tab_view_id, new_page.id)
    # Тук трябва да се отварят page properties и да се фокусира името
