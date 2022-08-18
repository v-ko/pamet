import pamet
from pamet.model.page import Page
from pamet.model.text_note import TextNote
from pamet.storage.file_system.repository import FSStorageRepository


def test_fs_repo_CRUD(tmp_path):
    fs_repo = FSStorageRepository.new(tmp_path)
    pamet.set_sync_repo(fs_repo)

    page = Page(id='test_page')
    pamet.insert_page(page)
    fs_repo.write_to_disk()

    assert fs_repo.path_for_page(page).exists()

    note = TextNote()
    note.text = 'test text'
    page.insert_note(note)
    fs_repo.write_to_disk()

    page_json = FSStorageRepository.serialize_page(page, page.notes(),
                                                   page.arrows())

    assert fs_repo.path_for_page(page).read_text() == page_json

    pamet.remove_page(page)
    fs_repo.write_to_disk()

    assert list(pamet.pages()) == []
