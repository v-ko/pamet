from dataclasses import dataclass

from misli import Entity, register_entity
from misli_gui.base_view import View
from pamet.entities import Note


@register_entity
@dataclass
class NoteViewModel(Entity):
    note: Note = None


class NoteView(View):
    def __init__(self, parent_id):
        View.__init__(
            self,
            parent_id=parent_id,
            initial_model=NoteViewModel()
        )

    @property
    def note(self):
        return self.displayed_model.note.copy()
