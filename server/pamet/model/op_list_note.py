from fusion.libs.entity import entity_type
from pamet.model.text_note import TextNote


@entity_type
class OtherPageListNote(TextNote):
    @property
    def text(self) -> str:
        return '*Other page links*'

    @text.setter
    def text(self, new_text: str):
        raise Exception
