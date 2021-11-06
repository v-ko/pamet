from .model import *
from . import views
from . import context
from . import commands

from misli.gui import KeyBinding
from pamet import commands

default_key_bindings = [
    KeyBinding('N', commands.create_new_note, conditions='pageFocus'),
    KeyBinding('Ctrl+N', commands.create_new_page, conditions='pageFocus'),
    KeyBinding('Ctrl+S',
               commands.save_page_properties,
               conditions='inPageProperties'),
]


def configure_for_qt():
    # Force view registration
    from pamet.views.map_page.widget import MapPageViewWidget
    from pamet.views.note.text.widget import TextNoteViewWidget
    from pamet.views.note.text.edit_widget import TextNoteEditViewWidget
