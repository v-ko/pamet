from misli.dataclasses import dataclass, Entity
from misli_gui.base_view import View
from pamet.entities import Note


@dataclass
class NoteViewModel(Entity):
    note: Note = None


class NoteView(View):
    def __init__(self, obj_class, parent_id):
        View.__init__(
            self,
            parent_id=parent_id,
            initial_model=NoteViewModel(),
            obj_class=obj_class
        )

    @property
    def note(self):
        return self.last_model.note.copy()
