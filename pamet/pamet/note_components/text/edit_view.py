from dataclasses import dataclass


from misli.basic_classes import Point
from misli import Entity, register_entity
from misli.gui.base_view import View

from pamet.entities import Note
from pamet.note_components import usecases


@register_entity
@dataclass
class TextNoteEditViewModel(Entity):
    create_mode: bool = False
    note: Note = None
    display_position: Point = None


class TextNoteEditView(View):
    view_class = 'TextNote'

    def __init__(self, parent_id):
        default_state = TextNoteEditViewModel()

        View.__init__(
            self,
            parent_id=parent_id,
            initial_model=default_state)

    @property
    def note(self):
        return self.displayed_model.note.copy()

    def _handle_esc_shortcut(self):
        usecases.abort_editing_note(self.id)
