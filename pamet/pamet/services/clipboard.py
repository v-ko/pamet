from PySide6.QtWidgets import QApplication
from misli.entity_library.entity import Entity
from pamet.model.image_note import ImageNote
from pamet.model.text_note import TextNote


class ClipboardService:
    def __init__(self):
        self._internal: list[Entity] = []

    def set_contents(self, entities: list[Entity]):
        if not entities:
            return

        self._internal = entities

        # The notes will be converted to markdown one fine day
        ext_clipboard_items = []
        for entity in entities:
            if isinstance(entity, TextNote):
                ext_clipboard_items.append(entity.text)
            elif isinstance(entity, ImageNote):
                ext_clipboard_items.append(entity.image_url)

        ext_content = '\n\n'.join(ext_clipboard_items)
        clipboard = QApplication.clipboard()
        clipboard.setText(ext_content)

    def get_contents(self) -> list[Entity]:
        return [entity.copy() for entity in self._internal]

    def convert_external(self) -> list[Entity]:
        pass
