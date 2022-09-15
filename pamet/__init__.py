from __future__ import annotations
from importlib import resources
import importlib.metadata

__version__ = importlib.metadata.version(__package__)

from typing import Generator, List, Union

import fusion
from fusion.change_aggregator import ChangeAggregator
from fusion.libs.entity.change import Change
from fusion.libs.channel import Channel
from fusion.storage.repository import Repository
from fusion.libs.entity import Entity
from fusion.extensions_loader import ExtensionsLoader
from fusion.libs.action import completed_root_actions
from fusion.logging import get_logger

from pamet.storage.base_repository import PametRepository
from pamet.storage.pamet_in_memory_repo import PametInMemoryRepository
from pamet.services.clipboard import ClipboardService
from pamet.services.search.base import BaseSearchService
from pamet import channels
from pamet.model.arrow import Arrow
from pamet.desktop_app import get_user_settings

from .note_view_lib import register_note_view_type, note_view_type
from .note_view_lib import note_view_type_by_state, note_state_type_by_view
from .note_view_lib import note_view_state_type_for_note

log = get_logger(__name__)

model_dir = resources.files('pamet') / 'model'
pamet_root = model_dir.parent
entity_types_loader = ExtensionsLoader(pamet_root)
entity_types_loader.load_all_recursively(model_dir)

clipboard = ClipboardService()

_search_service = None
_broken_entities = {}  # the entity as key, and exception as value

_sync_repo: PametRepository = None  # Should be set via the setter method

# _persistence_manager = PersistenceManager()
_undo_service = None

raw_entity_changes = Channel('__RAW_ENTITY_CHANGES__')

entity_change_aggregator = None


# Chain the entity changes channels
def unwrap_changeset(changeset: List[Change]):
    for change in changeset:
        channels.entity_changes_by_id.push(change)
        channels.entity_changes_by_parent_gid.push(change)


def setup():
    global entity_change_aggregator
    global clipboard

    entity_change_aggregator = ChangeAggregator(
        input_channel=raw_entity_changes,
        release_trigger_channel=completed_root_actions,
        changeset_output_channel=channels.entity_change_sets_per_TLA)
    clipboard = ClipboardService()

    channels.entity_change_sets_per_TLA.subscribe(unwrap_changeset)


setup()


def reset():
    setup()


def search_service() -> BaseSearchService:
    return _search_service


def set_search_service(service):
    global _search_service
    _search_service = service


def broken_entities():
    return _broken_entities


def entity_broke(entity: Entity, exception: Exception):
    if entity not in _broken_entities:
        log.error(f'Entity {entity} broke.')

    _broken_entities[entity] = exception


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


set_sync_repo(PametInMemoryRepository())


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
    fusion.call_delayed(_sync_repo.write_to_disk, 0)
    return _sync_repo.pages(**filter)


def page(page_gid: str) -> Union[Page, None]:
    if page_gid is None:
        return None
    if not isinstance(page_gid, str):
        raise Exception
    return _sync_repo.page(page_gid)


def default_page() -> Page:
    return _sync_repo.default_page()


def insert_page(page_: Page) -> Change:
    fusion.call_delayed(_sync_repo.write_to_disk, 0)
    return _sync_repo.insert_page(page_)


def remove_page(page_: Page) -> Change:
    fusion.call_delayed(_sync_repo.write_to_disk, 0)
    return _sync_repo.remove_page(page_)


def update_page(page_: Page) -> Change:
    fusion.call_delayed(_sync_repo.write_to_disk, 0)
    return _sync_repo.update_page(page_)


# -------------Notes CRUD-------------


def insert_note(note_: Note, page: Page = None) -> Change:
    fusion.call_delayed(_sync_repo.write_to_disk, 0)
    return _sync_repo.insert_note(note_, page)


def update_note(note_: Note) -> Change:
    fusion.call_delayed(_sync_repo.write_to_disk, 0)
    return _sync_repo.update_note(note_)


def remove_note(note_: Note) -> Change:
    fusion.call_delayed(_sync_repo.write_to_disk, 0)
    return _sync_repo.remove_note(note_)


def notes(page_: Page | str):
    return _sync_repo.notes(page_)


def note(page_: Page | str, own_id: str):
    return _sync_repo.note(page_, own_id)


# -------------Arrow CRUD-------------
def insert_arrow(arrow_: Arrow) -> Change:
    fusion.call_delayed(_sync_repo.write_to_disk, 0)
    return _sync_repo.insert_arrow(arrow_)


def update_arrow(arrow_: Arrow) -> Change:
    fusion.call_delayed(_sync_repo.write_to_disk, 0)
    return _sync_repo.update_arrow(arrow_)


def remove_arrow(arrow_: Arrow) -> Change:
    fusion.call_delayed(_sync_repo.write_to_disk, 0)
    return _sync_repo.remove_arrow(arrow_)


def arrows(page_: Page | str):
    return _sync_repo.arrows(page_)


def arrow(page_: Page | str, own_id: str):
    return _sync_repo.arrow(page_, own_id)


# ------------For changes--------------
def apply_change(change: Change):
    return _sync_repo.apply_change(change)
