
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
        try:
            text = self.content[TEXT]
        except KeyError:
            text = ''
            self.content[TEXT] = text
        return text

    @text.setter
    def text(self, new_text: str):
        self.content[TEXT] = new_text

    def text_rect(self, for_size: Point2D = None) -> Rectangle:
        if for_size:
            size = for_size
        else:
            size = self.rect().size()
        size -= Point2D(2 * NOTE_MARGIN, 2 * NOTE_MARGIN)
        return Rectangle(NOTE_MARGIN, NOTE_MARGIN, *size.as_tuple())
