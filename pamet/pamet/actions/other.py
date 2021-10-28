import misli
from misli.basic_classes import Point2D
from misli.gui.actions_library import action

import pamet
from pamet.model import Page
from pamet.model.text_note import TextNote
from pamet.desktop_app.config import get_config


@action('get_or_create_default_page')
def get_or_create_default_page():
    desktop_config = get_config()
    if 'home_page_id' in desktop_config:
        raise NotImplementedError()  # TODO: Load from id/url

    # TODO: If the repo is empty - put a help link as a first note
    # possibly with a "double-click to open link"
    pages = list(pamet.pages())
    if not pages:
        page = Page(name='notes')
        misli.insert(page)

        help_link_note = TextNote(parent_id=page.id, text='Mock help note')
        rect = help_link_note.rect()
        rect.move_center(Point2D(0, 0))
        help_link_note.set_rect(rect)
        misli.insert(help_link_note)
    else:
        page = pages[0]

    return page
