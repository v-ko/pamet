from copy import copy
from PySide6.QtWidgets import QApplication
from fusion.libs.entity import Entity
from pamet.desktop_app.mime_data_utils import entities_from_mime_data
from pamet.model.image_note import ImageNote
from pamet.model.text_note import TextNote
from fusion import get_logger

log = get_logger(__name__)


class ClipboardService:

    def __init__(self):
        self._internal: list[Entity] = []

    def set_contents(self, entities: list[Entity]):
        if not entities:
            return

        self._internal = copy(entities)

        # The notes will be converted to markdown one fine day
        ext_clipboard_items = []
        for entity in entities:
            if isinstance(entity, TextNote):
                ext_clipboard_items.append(entity.text)
            elif isinstance(entity, ImageNote):
                ext_clipboard_items.append(str(entity.image_url))

        ext_content = '\n\n'.join(ext_clipboard_items)
        clipboard = QApplication.clipboard()
        clipboard.setText(ext_content)

    def get_contents(self) -> list[Entity]:
        return [entity.copy() for entity in self._internal]

    def convert_external(self) -> list[Entity]:
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()
        return entities_from_mime_data(mime_data)
