import shutil
import pytest

import pamet
from pamet.services.file_system_storage import FSStorageRepository
from pamet import Page, Note

REPO_PATH = './tmp_mock_repo'


@pytest.fixture()
def fs_repo():
    fs_repo = FSStorageRepository.new(REPO_PATH)
    yield fs_repo

    shutil.rmtree(REPO_PATH)


def test_fs_repo_CRUD(fs_repo):
    page = Page(id='test_page')
    fs_repo.create_page(page, [])

    assert fs_repo.page_names() == [page.id]
    test_page, notes = fs_repo.get_page_and_notes(page.id)
    note_states = [n.state() for n in notes]
    assert (test_page.state(), note_states) == (page.state(), [])

    note = Note(page_id=page.id, text='test text')
    misli.insert(note)
    fs_repo.update_page(page, [note])

    test_page, test_notes = fs_repo.get_page_and_notes(page.id)
    note_states = [n.state() for n in test_notes]
    assert (test_page.state(), note_states) == (page.state(), [note.state()])

    fs_repo.delete_page(page.id)

    assert fs_repo.page_names() == []
