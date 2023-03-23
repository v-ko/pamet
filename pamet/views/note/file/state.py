from fusion.libs.state import view_state_type
from pamet.views.note.base.state import NoteViewState


@view_state_type
class FileNoteViewState(NoteViewState):
    preview_request_t: float = 0  # unix timestamp
