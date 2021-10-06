import pamet
from pamet import Page, Note


def test_page_CRUD():
    page = Page(id='test_page')
    misli.insert(page, [])

    assert [p.asdict() for p in pamet.pages()] == [page.asdict()]

    page.type_name = 'MapPage'
    pamet.update_page(id=page.id)

    assert [p.asdict() for p in pamet.pages()] == [page.asdict()]

    pamet.delete_page(page.id)

    assert pamet.pages() == []


def test_note_CRUD():
    page = Page(id='test_page')
    misli.insert(page, [])

    note = Note(page_id=page.id, text='test text')
    misli.insert(note)

    assert [n.asdict() for n in pamet.notes(page.id)] == [note.asdict()]

    note.text = 'test text changed'
    misli.update(**note.asdict())

    updated = pamet.note(page.id, note.id).asdict()

    assert updated == note.asdict()

    misli.remove(note)

    assert pamet.notes(page.id) == []
