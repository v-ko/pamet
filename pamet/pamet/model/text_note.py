
from misli import get_logger
from misli import entity_type
from misli.basic_classes.point2d import Point2D
from misli.basic_classes.rectangle import Rectangle
from pamet.constants import NOTE_MARGIN
from pamet.model.note import Note
log = get_logger(__name__)

TEXT = 'text'


@entity_type
class TextNote(Note):
    def __post_init__(self):
        super().__post_init__()
        if TEXT not in self.content:
            self.content[TEXT] = ''

    @property
    def text(self) -> str:
        return self.content[TEXT]

    @text.setter
    def text(self, new_text):
        self.content[TEXT] = new_text
