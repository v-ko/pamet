import misli
from misli.basic_classes import Point2D
from misli.gui.actions_library import action

from pamet.helpers import generate_page_name
from pamet.model import Page
from pamet.model.text_note import TextNote


@action('create_default_page')
def create_default_page():
    # TODO: If the repo is empty - put a help link as a first note
    # possibly with a "double-click to open link"

    page = Page(name=generate_page_name())
    misli.insert(page)

    help_link_note = TextNote(parent_id=page.id, text='Mock help note')
    rect = help_link_note.rect()
    rect.move_center(Point2D(0, 0))
    help_link_note.set_rect(rect)
    misli.insert(help_link_note)

    return page