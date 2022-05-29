from misli.basic_classes import Point2D
from misli.gui import view_state_type
from pamet.model.note import Note
from pamet.model.text_note import TextNote
from pamet.views.note.base_note_view import NoteViewState


@view_state_type
class NoteEditViewState(NoteViewState, TextNote):
    edited_note: Note = None
    create_mode: bool = False
    # display_position: Point2D = None
    # popup_position_center: Point2D = None

    def __post_init__(self):
        # That's just to avoid the exception in NoteViewState raised if no note
        # has been set up, which is irrelevant in this case, since we
        # reimplement the note property
        self.note_gid = self.edited_note.gid()
        super().__post_init__()

    @property
    def note(self):
        return self.edited_note.copy()
