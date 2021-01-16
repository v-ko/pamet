import misli
import pamet
from pamet.entities import Page, Note


def test_page_CRUD():
    page = Page(id='test_page')
    pamet.add_page(page, [])

    assert [p.state() for p in pamet.pages()] == [page.state()]

    page.obj_class = 'MapPage'
    pamet.update_page(id=page.id, obj_class='MapPage')

    assert [p.state() for p in pamet.pages()] == [page.state()]

    pamet.delete_page(page.id)

    assert pamet.pages() == []


def test_note_CRUD():
    page = Page(id='test_page')
    pamet.add_page(page, [])

    note = Note(page_id=page.id, text='test text')
    pamet.add_note(note)

    assert [n.state() for n in pamet.notes(page.id)] == [note.state()]

    note.text = 'test text changed'
    pamet.update_note(**note.state())

    updated = pamet.note(page.id, note.id).state()

    assert updated == note.state()

    pamet.delete_note(note)

    assert pamet.notes(page.id) == []
