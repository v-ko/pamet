from pathlib import Path
from typing import Union

from misli.extensions_loader import ExtensionsLoader
from misli.logging import get_logger
from .model import page, pages, create_note, set_sync_repo, set_async_repo
from .model import find, find_one, insert_note, insert_page, update_note
from .model import update_page, remove_note, remove_page
from .model import insert_arrow, remove_arrow, update_arrow
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


def configure_for_qt():
    # Force view registration
    from pamet.views.map_page.widget import MapPageWidget
    from pamet.views.note.text.widget import TextNoteWidget
    from pamet.views.note.text.edit_widget import CardNoteEditWidget
    from pamet.views.note.image.widget import ImageNoteWidget


def resource_path(subpath: Union[str, Path]):
    resource_dir_path = Path(__file__).parent / 'resources'
    resource_path = resource_dir_path / Path(subpath)

    if subpath.startswith('/'):
        subpath = subpath[1:]

    if not resource_path.exists():
        raise Exception('Resource not found')
    return resource_path
