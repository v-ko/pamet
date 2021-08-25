from dataclasses import dataclass


from misli.basic_classes import Point2D
from misli import Entity, register_entity
from pamet.note_components.base_note_view import NoteView

from pamet.entities import Note
from pamet.note_components import usecases


@register_entity
@dataclass
class TextNoteEditViewModel(Entity):
    create_mode: bool = False
    note: Note = None
    display_position: Point2D = None


class TextNoteEditView(NoteView):
    def __init__(self, parent_id):
        default_state = TextNoteEditViewModel()

        NoteView.__init__(
            self,
            parent_id=parent_id,
            initial_model=default_state)

    @property
    def note(self) -> Note:
        return self.displayed_model.note.copy()

    def _handle_esc_shortcut(self):
        usecases.abort_editing_note(self.id)
