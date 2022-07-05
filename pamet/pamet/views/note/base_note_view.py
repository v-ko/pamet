from dataclasses import field
from misli.basic_classes.point2d import Point2D
from misli.basic_classes.rectangle import Rectangle
from misli.gui.view_library.view import View
from misli.gui import ViewState, view_state_type
import pamet

from pamet.model import Note
from pamet.model.arrow import ArrowAnchorType


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

    def arrow_anchor(self, anchor_type: ArrowAnchorType) -> Point2D:
        """Returns the center position for a specific arrow anchor.

        Raises: Does not support the ArrowAnchorType.AUTO
        """
        rect: Rectangle = self.state().rect()

        match anchor_type:
            case ArrowAnchorType.MID_LEFT:
                return rect.top_left() + Point2D(0, rect.height() / 2)
            case ArrowAnchorType.TOP_MID:
                return rect.top_left() + Point2D(rect.width() / 2, 0)
            case ArrowAnchorType.MID_RIGHT:
                return rect.top_right() + Point2D(0, rect.height() / 2)
            case ArrowAnchorType.BOTTOM_MID:
                return rect.bottom_left() + Point2D(rect.width() / 2)
            case _:
                raise Exception
