from fusion.libs.state import view_state_type
from pamet.model.note import Note
from pamet.views.note.base.state import NoteViewState


@view_state_type
class NoteEditViewState(NoteViewState):
    new_note_dict: dict = None

    @property
    def create_mode(self):
        return bool(self.new_note_dict)

    def update_from_note(self, note: Note):
        note_dict = note.asdict()
        note_dict.pop('id')
        self.replace(**note_dict)
