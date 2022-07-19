from pathlib import Path
from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QImage, QPixmap, QResizeEvent
from PySide6.QtWidgets import QLabel
from misli.entity_library.change import Change
from misli.gui.utils.qt_widgets import bind_and_apply_state
from misli.gui.view_library.view_state import view_state_type
from misli.logging import get_logger

from pamet import register_note_view_type
from pamet.helpers import Url
from pamet.model.image_note import ImageNote
from pamet.views.note.base_note_view import NoteView, NoteViewState
from pamet.desktop_app import media_store

log = get_logger(__name__)


@view_state_type
class ImageNoteViewState(NoteViewState, ImageNote):
    pass


@register_note_view_type(state_type=ImageNoteViewState,
                         note_type=ImageNote,
                         edit=False)
class ImageNoteWidget(QLabel, NoteView):

    def __init__(self, parent, initial_state):
        QLabel.__init__(self, parent)
        NoteView.__init__(self, initial_state)
        self._image = None
        self._old_size = self.size()

        self.setWordWrap(True)
        self.setAlignment(Qt.AlignCenter)

        bind_and_apply_state(self, initial_state, self.on_state_change)

    def update_pixmap(self):
        if not self._image:
            return
        scaled_image = self._image.scaled(
            self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.setPixmap(QPixmap.fromImage(scaled_image))

    def resizeEvent(self, event: QResizeEvent):
        new_size = QSize(*self.state().rect().size().as_tuple())
        if new_size != self._old_size:
            self._old_size = new_size
            self.update_pixmap()

    def on_state_change(self, change: Change):
        state: ImageNoteViewState = change.last_state()

        if change.updated.color or change.updated.background_color:
            fg_col = QColor(*state.get_color().to_uint8_rgba_list())
            bg_col = QColor(*state.get_background_color().to_uint8_rgba_list())

            palette = self.palette()
            palette.setColor(self.backgroundRole(), bg_col)
            palette.setColor(self.foregroundRole(), fg_col)
            self.setPalette(palette)

        if change.updated.local_image_url:
            local_url: Url = state.local_image_url

            if local_url:
                local_path = Path(local_url.path)
                if local_url.is_internal():
                    local_path = media_store.path_for_internal_uri(local_url)

                if not local_path.exists():
                    self.setText(f'Local path missing: {local_path}')
                else:
                    self._image = QImage(local_path)
                    if self._image.isNull():
                        self.setText(
                            f'Could not load the image at {local_path}')
                        self._image = None
                        return
                    self.update_pixmap()

            else:
                self.setText(
                    'Image was not properly downloaded. Edit it to try again.')

        if change.updated.geometry:
            self.setGeometry(QRect(*state.geometry))
