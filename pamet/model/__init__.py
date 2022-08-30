from __future__ import annotations

from typing import Generator, List, Union

import fusion
from fusion.change_aggregator import ChangeAggregator
from fusion.entity_library.change import Change
from fusion.pubsub import Channel
from fusion.storage.repository import Repository

import pamet
from pamet import channels
from fusion import get_logger
from pamet.model.arrow import Arrow
from pamet.storage.pamet_in_memory_repo import PametInMemoryRepository
# from pamet.persistence_manager import PersistenceManager

log = get_logger(__name__)

_sync_repo: Repository = PametInMemoryRepository()
# _persistence_manager = PersistenceManager()
_undo_service = None

raw_entity_changes = Channel('__RAW_ENTITY_CHANGES__')

entity_change_aggregator = ChangeAggregator(
    input_channel=raw_entity_changes,
    release_trigger_channel=fusion.gui.channels.completed_root_actions,
    changeset_output_channel=channels.entity_change_sets_per_TLA)


# Chain the entity changes channels
def unwrap_changeset(changeset: List[Change]):
    for change in changeset:
        channels.entity_changes_by_id.push(change)
        channels.entity_changes_by_parent_gid.push(change)
        # channels.page_changes.push(change)


channels.entity_change_sets_per_TLA.subscribe(unwrap_changeset)


def undo_service():
    return _undo_service


def set_undo_service(undo_service_):
    global _undo_service
    _undo_service = undo_service_


def sync_repo():
    """Returns the synchronous repo"""
    return _sync_repo


def set_sync_repo(repository: Repository):
    """
    Set a repository, which will be used synchronously when calling for CRUD
    operations.
    """
    global _sync_repo
    repository.set_change_channel(raw_entity_changes)
    _sync_repo = repository


@log.traced
def async_repo():
    """Returns the asynchronous repository"""
    return _persistence_manager.async_repo


@log.traced
def set_async_repo(repo: Repository):
    """Set the secondary repository, that's called asynchronously to persist
    the changes.

    This is used for the GUI interfaces, where the changes are
    saved synchronously in the in-memory repo initially to avoid UI lag. And
    then pushed to the async repo too. The errors or delays from the async repo
    are handled by the PersistenceManager"""

    log.info('Setting repo to %s' % repo)
    _persistence_manager.async_repo = repo

    # Here the persistence manager should be connected to the entityTLA channel


# ------------Finds-----------------
def find(**filter):
    return _sync_repo.find(**filter)


def find_one(**filter):
    return _sync_repo.find_one(**filter)


# -------------Pages CRUD-------------
def pages(**filter) -> Generator[Page, None, None]:
    return _sync_repo.pages(**filter)


def page(page_gid: str | tuple) -> Union[Page, None]:
    return _sync_repo.page(page_gid)


def insert_page(page_: Page) -> Change:
    return _sync_repo.insert_page(page_)


def remove_page(page_: Page) -> Change:
    return _sync_repo.remove_page(page_)


def update_page(page_: Page) -> Change:
    return _sync_repo.update_page(page_)


# -------------Notes CRUD-------------

def insert_note(note_: Note, page: Page = None) -> Change:
    return _sync_repo.insert_note(note_, page)


def update_note(note_: Note) -> Change:
    return _sync_repo.update_note(note_)


def remove_note(note_: Note) -> Change:
    return _sync_repo.remove_note(note_)


def notes(page_: Page | str):
    return _sync_repo.notes(page_)


def note(page_: Page | str, own_id: str):
    return _sync_repo.note(page_, own_id)


# -------------Arrow CRUD-------------
def insert_arrow(arrow_: Arrow) -> Change:
    return _sync_repo.insert_arrow(arrow_)


def update_arrow(arrow_: Arrow) -> Change:
    return _sync_repo.update_arrow(arrow_)


def remove_arrow(arrow_: Arrow) -> Change:
    return _sync_repo.remove_arrow(arrow_)


def arrows(page_: Page | str):
    return _sync_repo.arrows(page_)


def arrow(page_: Page | str, own_id: str):
    return _sync_repo.arrow(page_, own_id)


# ------------For changes--------------
def apply_change(change: Change):
    return _sync_repo.apply_change(change)


# Validity checks
def arrow_validity_check():
    """Removes arrows with missing anchor notes. Must be performed after
    the repo has been initialized."""

    # Validity check on the arrow note anchors
    # If the note, that the anchor points to, is missing - skip arrow
    invalid_arrows = []
    for arrow in pamet.find(type=Arrow):
        if (arrow.has_tail_anchor() and not arrow.get_tail_note()) or\
                (arrow.has_head_anchor() and not arrow.get_head_note()):

            invalid_arrows.append(arrow)

    for arrow in invalid_arrows:
        log.error('Removing arrow because of an invalid note anchor: '
                  f'{arrow}')
        pamet.remove_arrow(arrow)
