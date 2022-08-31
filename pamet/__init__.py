from pathlib import Path
import importlib.metadata
__version__ = importlib.metadata.version(__package__)

from fusion.entity_library.entity import Entity
from fusion.extensions_loader import ExtensionsLoader
from fusion.logging import get_logger
from pamet.services.clipboard import ClipboardService
from pamet.services.search.base import BaseSearchService
from .model import sync_repo, async_repo, set_sync_repo, set_async_repo
from .model import page, pages, remove_page, update_page, insert_page
from .model import find, find_one
from .model import insert_note, remove_note, update_note, note, notes
from .model import insert_arrow, remove_arrow, update_arrow, arrow, arrows
from .model import apply_change, undo_service, set_undo_service

from .note_view_lib import register_note_view_type, note_view_type
from .note_view_lib import note_view_type_by_state, note_state_type_by_view
from .note_view_lib import note_view_state_type_for_note

log = get_logger(__name__)


pamet_root = Path(__file__).parent
# __version__ = (pamet_root / 'VERSION').read_text()

extensions_loader = ExtensionsLoader(pamet_root)
extensions_loader.load_all_recursively(pamet_root / 'model')

clipboard = ClipboardService()

_search_service = None
_broken_entities = {}  # the entity as key, and exception as value


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
