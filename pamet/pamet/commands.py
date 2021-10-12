from misli.gui import command
from pamet import actions


@command(title='Create new note', default_shortcut='N')
def create_new_note():
    actions.note.create_new_note(...)
