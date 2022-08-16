from __future__ import annotations

from copy import copy
from datetime import datetime
from typing import Generator, List, Union

import misli
from misli.change_aggregator import ChangeAggregator
from misli.entity_library.change import Change
from misli.pubsub import Channel
from misli.storage.in_memory_repository import InMemoryRepository
from misli.storage.repository import Repository

import pamet
from pamet import channels
from misli import entity_library
from misli import get_logger
from pamet.helpers import current_time
from pamet.model.arrow import Arrow
from pamet.services.undo import UndoService
# from pamet.persistence_manager import PersistenceManager

from .note import Note
from .page import Page  # So that they're accessible from the module

log = get_logger(__name__)

_sync_repo: Repository = InMemoryRepository()
# _persistence_manager = PersistenceManager()

raw_entity_changes = Channel('__RAW_ENTITY_CHANGES__')

entity_change_aggregator = ChangeAggregator(
    input_channel=raw_entity_changes,
    release_trigger_channel=misli.gui.channels.completed_root_actions,
    changeset_output_channel=channels.entity_change_sets_per_TLA)

undo_history = UndoService(channels.entity_change_sets_per_TLA)


# Chain the entity changes channels
def unwrap_changeset(changeset: List[Change]):
    for change in changeset:
        channels.entity_changes_by_id.push(change)
        channels.entity_changes_by_parent_gid.push(change)
        # channels.page_changes.push(change)


channels.entity_change_sets_per_TLA.subscribe(unwrap_changeset)


def sync_repo():
    """Returns the synchronous repo"""
    return _sync_repo


def set_sync_repo(repository: Repository):
    """
    Set a repository, which will be used synchronously when calling for CRUD
    operations.
    """
    global _sync_repo
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
    yield from _sync_repo.find(**filter)


def find_one(**filter):
    return _sync_repo.find_one(**filter)


# -------------Pages CRUD-------------
def pages(**filter) -> Generator[Page, None, None]:
    filter['type_name'] = Page.__name__
    return _sync_repo.find(**filter)


def page(**filter) -> Union[Page, None]:
    filter['type_name'] = Page.__name__
    return copy(_sync_repo.find_one(**filter))


def insert_page(page_: Page):
    change = _sync_repo.insert_one(page_)
    raw_entity_changes.push(change)


def remove_page(page_: Page):
    change = _sync_repo.remove_one(page_)
    raw_entity_changes.push(change)


def update_page(page_: Page):
    old_page = _sync_repo.find_one(id=page_.id)
    if not old_page:
        raise Exception('Can not update missing page.')

    if page_.name != old_page.name:
        page_.modified = current_time()

    change = _sync_repo.update_one(page_)
    raw_entity_changes.push(change)


# -------------Notes CRUD-------------
def create_note(**props):
    if 'page_id' not in props:
        raise Exception('Cannot create note without passing a page_id kwarg')

    type_name = pamet.note_type_from_props(props).__name__
    note_ = entity_library.from_dict(type_name, props)
    note_.created = current_time()
    note_.modified = current_time()
    change = _sync_repo.insert_one(note_)
    if not change:
        raise Exception('No change returned for the inserted note.')
    raw_entity_changes.push(change)
    return note_


def insert_note(note_: Note):
    change = _sync_repo.insert_one(note_)
    raw_entity_changes.push(change)


def update_note(note_: Note):
    old_note = _sync_repo.find_one(gid=note_.gid())
    if not old_note:
        raise Exception('Can not update missing note.')

    if note_.content != old_note.content:
        note_.modified = current_time()

    change = _sync_repo.update_one(note_)
    raw_entity_changes.push(change)


def remove_note(note_: Note):
    change = _sync_repo.remove_one(note_)
    raw_entity_changes.push(change)


# -------------Arrow CRUD-------------
def insert_arrow(arrow_: Arrow):
    change = _sync_repo.insert_one(arrow_)
    raw_entity_changes.push(change)


def update_arrow(arrow_: Arrow):
    old_arrow = _sync_repo.find_one(gid=arrow_.gid())
    if not old_arrow:
        raise Exception('Can not update missing arrow')

    change = _sync_repo.update_one(arrow_)
    raw_entity_changes.push(change)


def remove_arrow(arrow_: Arrow):
    change = _sync_repo.remove_one(arrow_)
    raw_entity_changes.push(change)


# ------------For changes--------------
def apply_change(change: Change):
    last_state = change.last_state()

    if change.is_create():
        _sync_repo.insert_one(last_state)
    elif change.is_update():
        _sync_repo.update_one(last_state)
    elif change.is_delete():
        _sync_repo.remove_one(last_state)

    raw_entity_changes.push(change)


# Validity checks
def arrow_validity_check():
    """Removes arrows with missing anchor notes. Must be performed after
    the repo has been initialized."""

    # Validity check on the arrow note anchors
    # If the note, that the anchor points to, is missing - skip arrow
    invalid_arrows = []
    for arrow in pamet.find(type_name=Arrow.__name__):
        if (arrow.has_tail_anchor() and not arrow.get_tail_note()) or\
                (arrow.has_head_anchor() and not arrow.get_head_note()):

            invalid_arrows.append(arrow)

    for arrow in invalid_arrows:
        log.error('Removing arrow because of an invalid note anchor: '
                  f'{arrow}')
        pamet.remove_arrow(arrow)
