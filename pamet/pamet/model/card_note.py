
from misli.entity_library import entity_type
from pamet.model.image_note import ImageNote
from pamet.model.text_note import TextNote


@entity_type
class CardNote(ImageNote, TextNote):
    pass
