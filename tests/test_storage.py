from copy import copy
import pytest

from fusion.storage.in_memory_repository import InMemoryRepository
import pamet
from pamet.model.note import Note
from pamet.model.page import Page
from pamet.model.text_note import TextNote
from pamet.storage.file_system.repository import FSStorageRepository


def test_in_memory_repo():
    repo = InMemoryRepository()

    page1 = Page()
    page2 = Page()

    note1a = Note.in_page(page1)
    note1b_for_update = TextNote.in_page(page1)
    note1c_for_removal = Note.in_page(page1)

    note2 = Note.in_page(page2)

    # Test the update and remove exceptions for missing entities
    with pytest.raises(Exception):
        repo.update_one(page1)

    with pytest.raises(Exception):
        repo.remove_one(page1)

    entities = [
        page1, page2, note1a, note1b_for_update, note1c_for_removal, note2
    ]
    # Add all entities
    for entity in entities:
        repo.insert_one(entity)

    # Test note immutability
    with pytest.raises(Exception):
        note1b_for_update.text = 'test'

    note1b_for_update = note1b_for_update.copy()
    note1b_for_update.text = 'test'
    repo.update_one(note1b_for_update)
    repo.remove_one(note1c_for_removal)

    expected_entities = copy(entities)
    expected_entities.remove(note1c_for_removal)

    # Test find operations

    # Find all
    assert set(repo.find()) == set(expected_entities)

    # Find using the global id index
    assert repo.find_one(gid=note1b_for_update.gid()).asdict() == \
        note1b_for_update.asdict()

    # Find using the parent_gid index
    assert set(repo.find(parent_gid=page1.gid())) == \
        set([note1a, note1b_for_update])

    # Find using the type name index
    assert set(repo.find(type=TextNote)) == \
        set([note1b_for_update])


def test_fs_repo_CRUD(tmp_path):
    fs_repo = FSStorageRepository.new(tmp_path)
    pamet.set_sync_repo(fs_repo)

    page = Page(id='test_page')
    pamet.insert_page(page)
    fs_repo.write_to_disk()

    assert fs_repo.path_for_page(page).exists()

    note = TextNote()
    note.text = 'test text'
    pamet.insert_note(note, page)
    fs_repo.write_to_disk()

    page_json = FSStorageRepository.serialize_page(page, pamet.notes(page),
                                                   pamet.arrows(page))

    assert fs_repo.path_for_page(page).read_text() == page_json

    pamet.remove_page(page)
    fs_repo.write_to_disk()

    assert list(pamet.pages()) == []
