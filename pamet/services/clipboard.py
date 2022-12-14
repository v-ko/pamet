from copy import copy
from PySide6.QtWidgets import QApplication
from fusion.libs.entity import Entity
from fusion.util.point2d import Point2D
from pamet.constants import ALIGNMENT_GRID_UNIT
from pamet.model.card_note import CardNote
from pamet.util import snap_to_grid
from pamet.util.url import Url
from pamet.model.image_note import ImageNote
from pamet.model.text_note import TextNote
from pamet.views.note.qt_helpers import minimal_nonelided_size


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
        entities = []

        if mime_data.hasImage():
            raise NotImplementedError
        elif mime_data.hasUrls():
            urls = mime_data.text().split('\n')
            for url in urls:
                note = TextNote()
                note.text = url
                parsed_url = Url(url)
                if parsed_url.has_web_schema():
                    note.url = url
                entities.append(note)
            return entities

        elif mime_data.hasText():  # This triggers for URLs too
            text = mime_data.text()
            text_sections = text.split('\n\n')

            for section in text_sections:
                note = TextNote()
                note.text = section
                # Single urls don't get detected by Qt
                if Url(section).has_web_schema():
                    note.url = section
                entities.append(note)

        # Autosize the notes and place them one under the other
        next_spawn_pos = Point2D(0, 0)
        for note in entities:
            rect = note.rect()

            # Autosize
            if isinstance(note, (TextNote, CardNote, ImageNote)):
                new_size = minimal_nonelided_size(note)
                rect.set_size(snap_to_grid(new_size))

            # Move under the last one
            rect.set_top_left(next_spawn_pos)

            # Update the spawn pos to be one unit under the last note
            next_spawn_pos = rect.bottom_left()
            next_spawn_pos += Point2D(0, ALIGNMENT_GRID_UNIT)

            # Insert the note
            note.set_rect(rect)

        return entities
