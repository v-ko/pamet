from .model import *
from . import views
from . import context
from . import commands

from misli.gui import KeyBinding
from pamet import commands

default_key_bindings = [
    KeyBinding('N', commands.create_new_note, conditions='pageFocus'),
    KeyBinding('Ctrl+N', commands.create_new_page, conditions='pageFocus'),
]
