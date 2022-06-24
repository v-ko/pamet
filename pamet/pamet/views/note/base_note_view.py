from dataclasses import field
from misli.basic_classes.point2d import Point2D
from misli.gui.view_library.view import View
from misli.gui import ViewState, view_state_type
import pamet

from pamet.model import Note


@view_state_type
class NoteViewState(ViewState, Note):
    note_gid: str = ''
    badges: list = field(default_factory=list, init=False, repr=False)

    def __post_init__(self):
        if not self.note_gid:
            raise Exception('All note views should have a mapped note.')

    def update_from_note(self, note: Note):
        self.replace(**note.asdict())

    def get_note(self):
        return pamet.find_one(gid=self.note_gid)


class NoteView(View):
    recieves_double_click_events: bool = False

    def __init__(self, initial_state):
        View.__init__(
            self,
            initial_state=initial_state
        )

    def left_mouse_double_click_event(self, position: Point2D):
        raise NotImplementedError
