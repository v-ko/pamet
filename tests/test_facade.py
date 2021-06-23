import pamet
from pamet import Page, Note


def test_page_CRUD():
    page = Page(id='test_page')
    pamet.add_page(page, [])

    assert [p.asdict() for p in pamet.pages()] == [page.asdict()]

    page.obj_class = 'MapPage'
    pamet.update_page(id=page.id, view_class='MapPage')

    assert [p.asdict() for p in pamet.pages()] == [page.asdict()]

    pamet.delete_page(page.id)

    assert pamet.pages() == []


def test_note_CRUD():
    page = Page(id='test_page')
    pamet.add_page(page, [])

    note = Note(page_id=page.id, text='test text')
    pamet.add_note(note)

    assert [n.asdict() for n in pamet.notes(page.id)] == [note.asdict()]

    note.text = 'test text changed'
    pamet.update_note(**note.asdict())

    updated = pamet.note(page.id, note.id).asdict()

    assert updated == note.asdict()

    pamet.delete_note(note)

    assert pamet.notes(page.id) == []
