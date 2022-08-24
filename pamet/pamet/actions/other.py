from misli.basic_classes import Point2D
from misli.gui.actions_library import action
import pamet

from pamet.helpers import generate_page_name
from pamet.model.page import Page
from pamet.model.text_note import TextNote


@action('create_default_page')
def create_default_page():
    # TODO: If the repo is empty - put a help link as a first note
    # possibly with a "double-click to open link"

    page = Page(name=generate_page_name())
    pamet.insert_page(page)

    help_link_note = TextNote(page_id=page.id)
    help_link_note.text = 'Mock help note'

    rect = help_link_note.rect()
    rect.move_center(Point2D(0, 0))
    help_link_note.set_rect(rect)
    pamet.insert_note(help_link_note)

    return page
