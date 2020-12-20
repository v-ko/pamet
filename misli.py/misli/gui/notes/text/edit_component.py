from misli.gui.base_component import Component
from misli.entities import Note
from misli.core.primitives import Point

from ... import usecases


class TextNoteEditComponent(Component):
    def __init__(self, parent_id):
        Component.__init__(
            self, parent_id=parent_id, obj_class='TextEdit')

        self.create_mode = False
        self.note = Note()
        self.display_position = Point(0, 0)

        self.add_state_keys(['note', 'display_position'])

    def _handle_ok_click(self):
        if self.create_mode:
            usecases.finish_creating_note(self.id, **self.note.state())
        else:
            usecases.finish_editing_note(self.id, **self.note.state())

    def _handle_esc_shortcut(self):
        usecases.abort_editing_note(self.id)
