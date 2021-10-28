from misli.basic_classes import Point2D
from misli.gui import wrap_and_register_view_state_type
from pamet.views.note.base_note_view import NoteView, NoteViewState

from pamet.model import Note
from pamet.actions import note


@wrap_and_register_view_state_type
class TextNoteEditViewState(NoteViewState):
    create_mode: bool = False
    display_position: Point2D = None


class TextNoteEditView(NoteView):
    def __init__(self, parent_id):
        default_state = TextNoteEditViewState()

        NoteView.__init__(
            self,
            parent_id=parent_id,
            initial_state=default_state)

    @property
    def note(self) -> Note:
        return self.state().note.copy()

    def _handle_esc_shortcut(self):
        note.abort_editing_note(self.id)
