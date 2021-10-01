from misli.gui.view_library.view import View
from pamet.entities import Note


class NoteView(View):
    def __init__(self, parent_id: str, initial_state):
        View.__init__(
            self,
            parent_id=parent_id,
            initial_state=initial_state
        )

    @property
    def note(self) -> Note:
        return self.state.note.copy()
