from typing import Callable

from misli.helpers import get_new_id, find_many_by_props, find_one_by_props
from misli.core.main_loop import NoMainLoop
from misli.entities import Page, Note
from misli.entities.change import Change, ChangeTypes
from misli.services.in_memory_storage import Repository

from misli import get_logger


log = get_logger(__name__)

line_spacing_in_pixels = 20
_repo = Repository()
_main_loop = NoMainLoop()

_pages = {}

_change_handlers = []
_change_stack = []


@log.traced
def set_main_loop(main_loop):
    global _main_loop
    _main_loop = main_loop


@log.traced
def repo():
    return _repo


@log.traced
def set_repo(repo: Repository):
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


def call_delayed(
        callback: Callable,
        delay: float,
        args: list = None,
        kwargs: dict = None):

    if args is None:
        args = []
    if kwargs is None:
        kwargs = {}

    log.debug('Will call %s delayed with %ssecs' % (callback.__name__, delay))
    _main_loop.call_delayed(callback, delay, args, kwargs)


# Change channel interface
@log.traced
def push_change(change: Change):
    log.info(str(change))
    _change_stack.append(change)
    call_delayed(_handle_changes, 0)


@log.traced
def on_change(handler: Callable):
    _change_handlers.append(handler)


@log.traced
def _handle_changes():
    if not _change_stack:
        return

    for handler in _change_handlers:
        handler(_change_stack)

    _change_stack.clear()


# -------------Pages CRUD-------------
@log.traced
def create_page(**page_state):
    # Create a new id both when missing key 'id' is missing or ==None
    _id = page_state.pop('id', None)
    page_state['id'] = _id or get_new_id()

    _page = Page(**page_state)

    load_page(_page)
    change = Change(ChangeTypes.CREATE, old_state={}, new_state=_page.state())
    push_change(change)

    return _page


@log.traced
def load_page(_page: Page):
    _pages[_page.id] = _page


# @log.traced
# def unload_page(page_id):
#     if page_id not in _pages:
#         log.error('Cannot unload missing page %s' % page_id)
#         return

#     del _pages[page_id]


@log.traced
def pages():
    return [page.copy() for pid, page in _pages.items()]


# @log.traced
def page(page_id: str):
    if page_id not in _pages:
        return None

    return _pages[page_id].copy()


@log.traced
def find_pages(**props):
    return find_many_by_props(_pages, **props)


@log.traced
def find_page(**props):
    return find_one_by_props(_pages, **props)


@log.traced
def update_page(**page_state):
    if 'id' not in page_state:
        log.error('Could not update note without a supplied id. '
                  'Given state: %s' % page_state)
        return

    _page = page(page_state['id'])
    old_state = _page.state()

    _page.set_state(**page_state)
    new_state = _page.state()

    _pages[_page.id].set_state(**new_state)

    change = Change(ChangeTypes.UPDATE, old_state, new_state)
    push_change(change)


@log.traced
def delete_page(page_id: str):
    _page = _pages.pop(page_id, None)

    if not _page:
        log.error('Could not delete missing page %s' % page_id)
        return

    change = Change(ChangeTypes.DELETE, old_state=_page.state(), new_state={})
    push_change(change)


# -------------Notes CRUD-------------
@log.traced
def create_note(**note_state):
    # Create a new id both when missing key 'id' is missing or ==None
    _id = note_state.pop('id', None)
    note_state['id'] = _id or get_new_id()

    page_id = note_state.get('page_id')
    if not page_id:
        raise Exception(
            'Cannot create note without page_id. State: %s' % note_state)

    note_state['page_id'] = page_id
    note = Note(**note_state)

    _pages[note.page_id].add_note(note)

    change = Change(ChangeTypes.CREATE, old_state={}, new_state=note.state())
    push_change(change)

    return note


@log.traced
def update_note(**note_state):
    if 'page_id' not in note_state or 'id' not in note_state:
        log.error('Could not update note without id and page_id parameters. '
                  'Given state: %s' % note_state)
        return

    note = Note(**note_state)
    old_state = page(note.page_id).note(note.id).state()

    note.set_state(**note_state)
    _pages[note.page_id].update_note(note)

    change = Change(ChangeTypes.UPDATE, old_state, new_state=note.state())
    push_change(change)


@log.traced
def delete_note(note: Note):
    _pages[note.page_id].remove_note(note)

    change = Change(ChangeTypes.DELETE, note.state(), new_state={})
    push_change(change)


# ---------Common-------------
def entity(entity_id):
    if entity_id in _pages:
        return page(entity_id)

    for pid, p in _pages.items():
        if entity_id in p.note_states:
            return p.note(entity_id)
