from misli import get_logger
from misli.gui import command
import pamet
from pamet import actions


log = get_logger(__name__)


@command(title='Create new note')
def create_new_note():
    tab = pamet.views.current_tab()
    if not tab:
        log.error('No tab open, cannot create a new note')
        return

    page_view = tab.page_view()
    if not page_view:
        log.error('No page view, cannot create a new note')
        return

    actions.note.create_new_note(page_view.id, page_view.mouse_position())


@command(title='Create new page')
def create_new_page():
    pass
