from misli_gui.base_view import View
from pamet.entities import Note
from misli.basic_classes import Point
from misli.dataclasses import dataclass, Entity

from pamet.note_components import usecases


@dataclass
class TextNoteEditViewModel(Entity):
    create_mode: bool = False
    note: Note
    display_position: Point


class TextNoteEditView(View):
    def __init__(self, parent_id):
        default_state = TextNoteEditViewModel()

        View.__init__(
            self,
            parent_id=parent_id,
            obj_class='TextEdit',
            initial_model=default_state)

    @property
    def note(self):
        return self.last_model.note.copy()

    def _handle_esc_shortcut(self):
        usecases.abort_editing_note(self.id)
