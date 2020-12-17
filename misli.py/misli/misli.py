from misli.core.main_loop import NoMainLoop
from misli.objects import Page, Note
from misli.objects.change import Change, ChangeTypes
from misli.services.in_memory_storage import Repository

from misli import get_logger


log = get_logger(__name__)

line_spacing_in_pixels = 20
_repo = Repository()
_main_loop = NoMainLoop()

_pages = {}

_change_handlers = []
_change_stack = []


def set_main_loop(main_loop):
    global _main_loop
    _main_loop = main_loop


def repo():
    return _repo


def set_repo(repo):
    global _repo
    log.info('Setting repo to %s' % repo.path)

    if _pages:
        log.error('Cannot change repo while there are pages loaded')
        return

    _repo = repo

    # Load the pages from the new repo
    for page_id in repo.page_ids():
        page = Page(**repo.page_state(page_id))
        _pages[page.id] = page


def call_delayed(callback, delay, args=None, kwargs=None):
    if args is None:
        args = []
    if kwargs is None:
        kwargs = {}

    _main_loop.call_delayed(callback, delay, args, kwargs)


# Change channel interface
def push_change(change):
    _change_stack.append(change)
    call_delayed(_handle_changes, 0)


def on_change(handler):
    _change_handlers.append(handler)


def _handle_changes():
    if not _change_stack:
        return

    for handler in _change_handlers:
        handler(_change_stack)

    _change_stack.clear()


# -------------Pages CRUD-------------
def create_page(**page_state):
    _page = Page(**page_state)

    load_page(_page)
    change = Change(ChangeTypes.CREATE, old_state={}, new_state=_page.state())
    push_change(change)

    return _page


def load_page(_page):
    _pages[_page.id] = _page


# def unload_page(page_id):
#     if page_id not in _pages:
#         log.error('Cannot unload missing page %s' % page_id)
#         return

#     del _pages[page_id]


def pages():
    return [page for pid, page in _pages.items()]


def page(page_id):
    if page_id not in _pages:
        return None

    return _pages[page_id]


def update_page(page_id, **page_state):
    _page = page(page_id)
    old_state = _page.state()

    change = Change(ChangeTypes.UPDATE, old_state, page_state)
    push_change(change)


def delete_page(page_id):
    _page = _pages.pop(page_id, None)

    if not _page:
        log.error('Could not delete missing page %s' % page_id)
        return

    change = Change(ChangeTypes.DELETE, old_state=_page.state(), new_state={})
    push_change(change)


# -------------Notes C_UD-------------
def create_note(**note_state):
    page_id = note_state.pop('page_id', None)
    if not page_id:
        log.error('Cannot create note without page_id. State: %s' % note_state)
        return

    _page = page(page_id)
    note_state['page_id'] = page_id
    note = Note(**note_state)

    _page.add_note(note)

    change = Change(ChangeTypes.CREATE, old_state={}, new_state=note.state())
    push_change(change)

    return note


def update_note(**note_state):
    page_id = note_state.pop('page_id', None)
    note_id = note_state.pop('id', None)

    if not page_id or not note_id:
        log.error('Could not update note without id and page_id parameters. '
                  'Given state: %s' % note_state)
        return

    _page = page(page_id)
    note = _page.note(note_id)
    old_state = note.state()

    note.set_state(**note_state)

    change = Change(ChangeTypes.UPDATE, old_state, new_state=note.state())
    push_change(change)


def delete_note(note_id, page_id):
    _page = page(page_id)
    note = _page.note(note_id)

    _page.remove_note(note)

    change = Change(ChangeTypes.DELETE, note.state(), new_state={})
    push_change(change)
