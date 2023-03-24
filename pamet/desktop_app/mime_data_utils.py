from __future__ import annotations
import hashlib
from pathlib import Path

from PySide6.QtGui import QImageReader, QImage
from PySide6.QtCore import QMimeData
from fusion.libs.entity import Entity
from fusion.util.point2d import Point2D

import pamet
from pamet.desktop_app.util import jpeg_blob_from_image
from pamet.model.card_note import CardNote
from pamet.model.image_note import ImageNote
from pamet.model.text_note import TextNote
from pamet.util import snap_to_grid
from pamet.constants import ALIGNMENT_GRID_UNIT
from pamet.util.url import Url
from pamet.views.note.qt_helpers import minimal_nonelided_size
from fusion import get_logger

log = get_logger(__name__)


def entities_from_mime_data(mime_data: QMimeData) -> list[Entity]:
    entities = []

    if mime_data.hasImage():
        try:
            image = mime_data.imageData()
            if image.isNull():
                raise Exception('Could not load image from clipboard')

            blob = jpeg_blob_from_image(image)
            local_path = pamet.desktop_app.media_store().save_blob(
                blob, 'jpg', cache_subfolder_name='__pasted_images__')
        except Exception as e:
            log.error(f'Failed to save image from clipboard: {e}')
            return []

        image_note = ImageNote()
        image_note.local_image_url = local_path
        image_note.image_size = Point2D(image.size().width(),
                                        image.size().height())

        image_note.image_md5 = hashlib.md5(blob).hexdigest()

        entities.append(image_note)

    elif mime_data.hasUrls():
        # urls: list[str] = mime_data.text().split('\n')
        for url in mime_data.urls():
            # Check if it's a local file
            as_local_path = Path(url.toLocalFile())
            if as_local_path.exists():

                # Check if it's an image
                suffix = as_local_path.suffix.lower()
                suffix = suffix[1:] if suffix else suffix
                if (suffix in QImageReader.supportedImageFormats()):
                    note = ImageNote()
                    # Read to qimage
                    image_data = as_local_path.read_bytes()
                    image = QImage.fromData(image_data)
                    if image.isNull():
                        log.error(f'Could not load image from {as_local_path}')
                        continue

                    # Get md5
                    md5sum = hashlib.md5(image_data).hexdigest()

                    note.local_image_url = str(as_local_path)
                    note.image_size = Point2D(image.size().width(),
                                              image.size().height())
                    note.image_md5 = md5sum

                else:
                    # TODO: Support other file types
                    continue

            else:
                note = TextNote()
                note.text = url

                parsed_url = Url(url)
                if parsed_url.has_web_schema():
                    note.url = url

            entities.append(note)

    elif mime_data.hasText():  # This triggers for URLs too
        text = mime_data.text()
        text_sections = text.split('\n\n')

        for section in text_sections:
            if not section.strip():
                continue
            note = TextNote()
            note.text = section.strip()
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
