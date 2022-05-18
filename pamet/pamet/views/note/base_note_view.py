from misli.gui.view_library.view import View
from misli.gui import ViewState, view_state_type
import pamet

from pamet.model import Note


@view_state_type
class NoteViewState(ViewState, Note):
    note_gid: str = ''

    def __post_init__(self):
        if not self.note_gid:
            raise Exception('All note views should have a mapped note.')

    @property
    def note(self):
        return pamet.find_one(gid=self.note_gid)


class NoteView(View):
    def __init__(self, parent: str, initial_state):
        View.__init__(
            self,
            parent=parent,
            initial_state=initial_state
        )

        if not initial_state.note:
            raise Exception('Is this usecase acceptable or a bug?')
