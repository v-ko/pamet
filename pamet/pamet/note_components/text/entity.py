from dataclasses import dataclass

from misli import get_logger
from misli import register_entity
from pamet.entities.note import Note
log = get_logger(__name__)

TEXT = 'text'


@register_entity
@dataclass
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
