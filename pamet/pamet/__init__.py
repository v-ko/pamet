from pathlib import Path

from misli.extensions_loader import ExtensionsLoader
from misli.logging import get_logger
from pamet.services.clipboard import ClipboardService
from pamet.services.search.base import BaseSearchService
from .model import sync_repo, async_repo, set_sync_repo, set_async_repo
from .model import page, pages, remove_page, update_page, insert_page
from .model import find, find_one, create_note
from .model import insert_note, remove_note, update_note, note, notes
from .model import insert_arrow, remove_arrow, update_arrow, arrow, arrows
from .model import apply_change, undo_history

from .note_view_lib import register_note_view_type, note_view_type
from .note_view_lib import note_view_type_by_state, note_state_type_by_view
from .note_view_lib import note_view_state_type_for_note, note_type_from_props

log = get_logger(__name__)
# from misli.gui import KeyBinding
# from pamet.views.note.base_note_view import NoteViewState

default_key_bindings = [
    # KeyBinding('N', commands.create_new_note, conditions='pageFocus'),
    # KeyBinding('Ctrl+N', commands.create_new_page, conditions='pageFocus'),
    # KeyBinding('Ctrl+S',
    #            commands.save_page_properties,
    #            conditions='inPageProperties'),
    # KeyBinding('E', commands.edit_selected_notes, conditions='notesSelected')
]

pamet_root = Path(__file__).parent
extensions_loader = ExtensionsLoader(pamet_root)
extensions_loader.load_all_recursively(pamet_root / 'model')

clipboard = ClipboardService()

_search_service = None


def search_service() -> BaseSearchService:
    return _search_service


def set_search_service(service):
    global _search_service
    _search_service = service
