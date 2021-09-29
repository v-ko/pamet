from misli.gui.view import View
from pamet.entities import Note


class NoteView(View):
    def __init__(self, parent_id: str, initial_model):
        View.__init__(
            self,
            parent_id=parent_id,
            initial_model=initial_model
        )

    @property
    def note(self) -> Note:
        return self.state.note.copy()
