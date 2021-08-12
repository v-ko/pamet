from dataclasses import dataclass

from misli import get_logger
from misli import register_entity
from pamet.entities.note import Note
log = get_logger(__name__)


@register_entity
@dataclass
class TextNote(Note):
    text: str = ''
