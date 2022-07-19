
from misli import get_logger
from misli import entity_type
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
