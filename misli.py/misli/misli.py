from misli.objects import Page, Note
from misli.objects.change import Change, ChangeTypes

from misli import logging
log = logging.getLogger(__name__)


class MainLoop():
    def call_delayed(self, callback, delay):
        raise NotImplementedError()


_repo = None
_change_handlers = []
_change_stack = []
line_spacing_in_pixels = 20
_main_loop = MainLoop()


def call_delayed(callback, delay):
    _main_loop.call_delayed(callback, delay)


def set_main_loop(main_loop):
    global _main_loop
    _main_loop = main_loop


def set_call_delayed_implementation(implementation):
    global call_delayed
    call_delayed = implementation


def repo():
    return _repo


def set_repo(repo):
    global _repo
    log.info('Setting repo to %s' % repo.path)
    _repo = repo


def on_change(handler):
    _change_handlers.append(handler)


def create_page(id, obj_class, **page_state):
    if not page_state:
        page_state = {}
    page_state['id'] = id
    page_state['obj_class'] = obj_class

    page = Page(**page_state)
    _repo.load_page(page)
    _repo.save_page(page)
    return page


def page(page_id):
    return _repo.page(page_id)


def pages():
    return _repo.pages()


def _handle_changes():
    if not _change_stack:
        return

    for handler in _change_handlers:
        handler(_change_stack)

    _change_stack.clear()


def push_change(change):
    _change_stack.append(change)
    call_delayed(_handle_changes, 0)


def update_page(page_id, **page_state):
    _page = page(page_id)
    old_state = _page.state()

    if page_state:
        _page.set_state(**page_state)

    change = Change(ChangeTypes.UPDATE, old_state, page_state)
    push_change(change)


def delete_page(page_id):
    _page = page(page_id)
    _repo.delete_page(_page)


def create_note(page_id, **note_state):
    _page = page(page_id)
    note_state['page_id'] = page_id
    note = Note(**note_state)

    _page.add_note(note)

    change = Change(ChangeTypes.CREATE, old_state={}, new_state=note.state())
    push_change(change)

    return note


def update_note(note_id, page_id, **note_state):
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
