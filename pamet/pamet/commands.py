from misli import get_logger
from misli.gui import command
import pamet
from pamet import actions


log = get_logger(__name__)


def current_tab_and_page_views():
    tab = pamet.views.current_tab()
    if not tab:
        raise Exception('There\'s no open tab.')

    page_view = tab.page_view()
    if not page_view:
        raise Exception('No page view.')

    return tab, page_view


@command(title='Create new note')
def create_new_note():
    tab, page_view = current_tab_and_page_views()
    actions.note.create_new_note(page_view.id, page_view.mouse_position())


@command(title='Create new page')
def create_new_page():
    tab, page_view = current_tab_and_page_views()
    actions.tab.create_new_page(tab.id, page_view.mouse_position())
