from misli_gui.base_component import Component
from pamet.entities import Note
from misli.basic_classes import Point
from misli.dataclasses import dataclass, Entity

from pamet.note_components import usecases


@dataclass
class TextNoteEditComponentState(Entity):
    create_mode: bool = False
    note: Note
    display_position: Point


class TextNoteEditComponent(Component):
    def __init__(self, parent_id):
        default_state = TextNoteEditComponentState()

        Component.__init__(
            self,
            parent_id=parent_id,
            obj_class='TextEdit',
            default_state=default_state)

    @property
    def note(self):
        return self._state.note.copy()

    def _handle_esc_shortcut(self):
        usecases.abort_editing_note(self.id)
