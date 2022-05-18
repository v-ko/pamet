from datetime import datetime
from site import execsitecustomize
from typing import List
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
from pamet.persistence_manager import PersistenceManager

from .note import Note
from .page import Page  # So that they're accessible from the module

log = get_logger(__name__)

_sync_repo: Repository = InMemoryRepository()
_persistence_manager = PersistenceManager

raw_entity_changes = Channel('__RAW_ENTITY_CHANGES__')

entity_change_aggregator = ChangeAggregator(
    input_channel=raw_entity_changes,
    release_trigger_channel=misli.gui.channels.completed_root_actions,
    changeset_output_channel=channels.entity_changesets_per_TLA)


# Chain the entity changes channels
def unwrap_changeset(changeset: List[Change]):
    for change in changeset:
        channels.entity_changes_by_id.push(change)
        channels.entity_changes_by_parent_gid.push(change)


channels.entity_changesets_per_TLA.subscribe(unwrap_changeset)


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


# def publish_entity_change(change: Change):
#     pamet.channels.entity_changes_by_id.push(change)
#     pamet.channels.entity_changes_by_parent_gid.push(change)


# ------------Finds-----------------
def find(**filter):
    yield from _sync_repo.find(**filter)


def find_one(**filter):
    return _sync_repo.find_one(**filter)


# -------------Pages CRUD-------------
def pages(**filter):
    filter['type_name'] = Page.__name__
    return _sync_repo.find(**filter)


def page(**filter):
    filter['type_name'] = Page.__name__
    return _sync_repo.find_one(**filter)


def insert_page(page_: Page):
    change = _sync_repo.insert_one(page_)
    raw_entity_changes.push(change)


def remove_page(page_: Page):
    change = _sync_repo.remove_one(page_)
    raw_entity_changes.push(change)


def update_page(page_: Page):
    change = _sync_repo.update_one(page_)
    raw_entity_changes.push(change)


# -------------Notes CRUD-------------
def create_note(**props):
    if 'page_id' not in props:
        raise Exception('Cannot create note without passing a page_id kwarg')

    type_name = pamet.note_type_from_props(props).__name__
    note_ = entity_library.from_dict(type_name, props)
    note_.time_created = datetime.now()
    note_.time_modified = datetime.now()
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
    if note_.content != old_note.content:
        note_.time_modified = datetime.now_()
    change = _sync_repo.update_one(note_)
    raw_entity_changes.push(change)


def remove_note(note_: Note):
    change = _sync_repo.remove_one(note_)
    raw_entity_changes.push(change)
