from misli.gui.view_library.view import View
from misli.gui import ViewState, register_view_state_type

from pamet.model import Note


@register_view_state_type
class NoteViewState(ViewState):
    def __post_init__(self):
        if not self.mapped_entity:
            self.mapped_entity = Note()

    @property
    def note(self):
        return self.mapped_entity

    @note.setter
    def note(self, new_note):
        self.mapped_entity = new_note


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
