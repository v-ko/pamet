from fusion.util import Point2D
from fusion.libs.action import action
import pamet

from pamet.util import generate_page_name
from pamet.model.page import Page
from pamet.model.text_note import TextNote


@action('create_default_page')
def create_default_page():
    # TODO: If the repo is empty - put a help link as a first note
    # possibly with a "double-click to open link"

    page = Page(name=generate_page_name())
    pamet.insert_page(page)

    help_link_note = TextNote.in_page(page)
    help_link_note.text = 'Mock help note'

    rect = help_link_note.rect()
    rect.move_center(Point2D(0, 0))
    help_link_note.set_rect(rect)
    pamet.insert_note(help_link_note)

    return page
