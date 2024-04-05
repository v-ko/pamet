from copy import copy
from PySide6.QtWidgets import QApplication
from fusion.libs.entity import Entity
from pamet.desktop_app.mime_data_utils import entities_from_mime_data
from pamet.model.card_note import CardNote
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

        def text_note_to_markdown(text_note: TextNote) -> str:
            if not text_note.url.is_empty():
                return f'[{text_note.text}]({text_note.url})'
            else:
                return text_note.text

        def image_note_to_markdown(image_note: ImageNote) -> str:
            text = f'image_{image_note.own_id}'
            markdown = f'![{text}]({image_note.image_url})'
            if not image_note.url.is_empty():
                markdown = f'[{markdown}]({image_note.url})'
            return markdown

        # The notes will be converted to markdown one fine day
        ext_clipboard_items = []
        for entity in entities:
            if isinstance(entity, CardNote):
                image_markdown = image_note_to_markdown(entity)
                text_markdown = text_note_to_markdown(entity)
                if len(text_markdown) > 200:
                    markdown = '| <!-- --> | <!-- --> |\n'
                    markdown += '| --- | --- |\n'
                    markdown += f'| {image_markdown} | {text_markdown} |'
                else:
                    markdown = f'| {image_markdown} |\n'
                    markdown += '| --- |\n'
                    markdown += f'| {text_markdown} |\n'
                ext_clipboard_items.append(markdown)

            elif isinstance(entity, TextNote):
                markdown = text_note_to_markdown(entity)
                ext_clipboard_items.append(markdown)

            elif isinstance(entity, ImageNote):
                markdown = image_note_to_markdown(entity)
                ext_clipboard_items.append(markdown)

        ext_content = '\n\n'.join(ext_clipboard_items)
        clipboard = QApplication.clipboard()
        clipboard.setText(ext_content)

    def get_contents(self) -> list[Entity]:
        return [entity.copy() for entity in self._internal]

    def convert_external(self) -> list[Entity]:
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()
        return entities_from_mime_data(mime_data)
