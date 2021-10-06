from dataclasses import dataclass


from misli.basic_classes import Point2D
from misli.gui import register_view_state_type
from pamet.note_components.base_note_view import NoteView, NoteViewState

from pamet.model import Note
from pamet.note_components import usecases


@register_view_state_type
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
        return self.state.note.copy()

    def _handle_esc_shortcut(self):
        usecases.abort_editing_note(self.id)
