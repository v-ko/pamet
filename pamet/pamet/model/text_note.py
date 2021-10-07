from misli import get_logger
from misli import wrap_and_register_entity_type
from pamet.model.note import Note
log = get_logger(__name__)

TEXT = 'text'


@wrap_and_register_entity_type
class TextNote(Note):
    def __post_init__(self):
        if TEXT not in self.content:
            self.text = ''

    @property
    def text(self) -> str:
        return self.content[TEXT]

    @text.setter
    def text(self, new_text):
        self.content[TEXT] = new_text
