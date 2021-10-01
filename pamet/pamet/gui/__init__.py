from misli.gui import EntityToViewMapping


entity_to_view_mapping = EntityToViewMapping()

from .helpers import create_and_bind_edit_view, create_and_bind_note_view
from .helpers import create_and_bind_page_view
from .actions import update_views_for_note_changes
from .actions import update_views_for_page_changes
