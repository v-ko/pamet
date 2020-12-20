import os
import shutil
import pytest

from misli.services.file_system_storage import FSStorageRepository
from misli.entities import Page, Note


@pytest.fixture()
def fs_repo():
    REPO_PATH = './tmp_mock_repo'

    if os.path.exists(REPO_PATH) and os.listdir(REPO_PATH):
        shutil.rmtree(REPO_PATH)

    fs_repo = FSStorageRepository.create(REPO_PATH)
    yield fs_repo

    shutil.rmtree(REPO_PATH)


def test_fs_repo_CRUD(fs_repo):
    page = Page(id='test_page')
    fs_repo.create_page(**page.state())

    assert fs_repo.page_ids() == [page.id]
    assert fs_repo.page_state(page.id) == page.state()

    note = Note(page_id=page.id, text='test text')
    page.add_note(note)
    fs_repo.update_page(**page.state(include_notes=True))

    assert fs_repo.page_state(page.id) == page.state(include_notes=True)

    fs_repo.delete_page(page.id)

    assert fs_repo.page_ids() == []
