from copy import copy
import pamet
from pamet.model.page import Page
from pamet.model.text_note import TextNote
from pamet.storage.pamet_in_memory_repo import PametInMemoryRepository


def test_page_CRUD():
    fs_repo = PametInMemoryRepository()
    pamet.set_sync_repo(fs_repo)

    page = Page(name='test_page')
    pamet.insert_page(copy(page))
    assert [p.asdict() for p in pamet.pages()] == [page.asdict()]

    page.name = 'test_page_updated'
    pamet.update_page(page)
    assert [p.asdict() for p in pamet.pages()] == [page.asdict()]

    pamet.remove_page(page)
    assert list(pamet.pages()) == []


def test_note_CRUD():
    fs_repo = PametInMemoryRepository()
    pamet.set_sync_repo(fs_repo)

    page = Page(name='test_page')
    pamet.insert_page(page)

    note = TextNote.in_page(page)
    note.text = 'test text'
    pamet.insert_note(copy(note))
    assert [n.asdict() for n in pamet.notes(page)] == [note.asdict()]

    note.text = 'test text changed'
    pamet.update_note(note)
    assert pamet.find_one(gid=note.gid()).asdict() == note.asdict()

    pamet.remove_note(note)
    assert pamet.find_one(gid=note.gid()) is None
