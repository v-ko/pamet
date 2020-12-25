import misli
from misli.entities import Page, Note


def test_page_CRUD():
    page_state = Page(id='test_page').state()
    page = misli.create_page(**page_state)

    assert misli.pages() == [page]

    page.obj_class = 'MapPage'
    misli.update_page(page.id, obj_class='MapPage')

    assert misli.pages() == [page]

    misli.delete_page(page.id)

    assert misli.pages() == []


def test_note_CRUD():
    page_state = Page(id='test_page').state()
    page = misli.create_page(**page_state)

    note_state = Note(page_id=page.id, text='test text').state()
    note = misli.create_note(**note_state)

    assert misli.page(page.id).note_states == {note.id: note.state()}

    note.text = 'test text changed'
    misli.update_note(**note.state())

    updated = misli.page(page.id).note(note.id).state()

    assert updated == note.state()

    misli.delete_note(note)

    assert page.notes() == []
