from copy import copy

import pytest
from fusion.storage.in_memory_store import InMemoryStore

from pamet.model.card_note import CardNote
from pamet.model.note import Note
from pamet.model.page import Page


def test_in_memory_repo():
    repo = InMemoryStore()

    page1 = Page()
    page2 = Page()

    note1a = Note.create(page1.id)
    note1b_for_update = CardNote.create(page1.id)
    note1c_for_removal = Note.create(page1.id)

    note2 = Note.create(page2.id)

    # Test the update and remove exceptions for missing entities
    with pytest.raises(Exception):
        repo.update_one(page1)

    with pytest.raises(Exception):
        repo.remove_one(page1)

    entities = [page1, page2, note1a, note1b_for_update, note1c_for_removal, note2]
    # Add all entities
    for entity in entities:
        repo.insert_one(entity)

    # Test that entity id is frozen
    with pytest.raises(Exception):
        note1b_for_update.id = "new_id"

    note1b_for_update = note1b_for_update.copy()
    note1b_for_update.text = "test"
    repo.update_one(note1b_for_update)
    repo.remove_one(note1c_for_removal)

    expected_entities = copy(entities)
    expected_entities.remove(note1c_for_removal)

    # Test find operations

    # Find all
    assert set(repo.find()) == set(expected_entities)

    # Find using the global id index
    assert repo.find_one(id=note1b_for_update.id).asdict() == note1b_for_update.asdict()

    # Find using the parent_id index
    assert set(repo.find(parent_id=page1.id)) == set([note1a, note1b_for_update])

    # Find using the type name index
    assert set(repo.find(type=CardNote)) == set([note1b_for_update])
