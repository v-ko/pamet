from misli.basic_classes import Point2D
from misli.gui import view_state_type
from pamet.model.note import Note
from pamet.model.text_note import TextNote
from pamet.views.note.base_note_view import NoteView, NoteViewState


@view_state_type
class TextNoteEditViewState(NoteViewState, TextNote):
    edited_note: Note = None
    create_mode: bool = False
    display_position: Point2D = None

    def __post_init__(self):
        self.note_gid = self.edited_note.gid()
        super().__post_init__()

    @property
    def note(self):
        return self.edited_note.copy()
