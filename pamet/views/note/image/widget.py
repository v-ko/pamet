from pathlib import Path
from PySide6.QtCore import QRect, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QPaintEvent, QPainter
from fusion.libs.entity.change import Change
from fusion.platform.qt_widgets import bind_and_apply_state
from fusion.libs.state import view_state_type
from fusion.logging import get_logger
from fusion.util.point2d import Point2D

from pamet import register_note_view_type
from pamet.desktop_app import media_store
from pamet.model.image_note import ImageNote
from pamet.views.note.base.view import NoteView
from pamet.views.note.file.state import FileNoteViewState
from pamet.views.note.image.image_label import ImageLabel
from pamet.views.note.qt_helpers import draw_link_decorations

log = get_logger(__name__)


@view_state_type
class ImageNoteViewState(FileNoteViewState, ImageNote):
    pass


@register_note_view_type(state_type=ImageNoteViewState,
                         note_type=ImageNote,
                         edit=False)
class ImageNoteWidget(ImageLabel, NoteView):

    def __init__(self, parent, initial_state):
        ImageLabel.__init__(self, parent)
        NoteView.__init__(self, parent, initial_state)

        bind_and_apply_state(self, initial_state, self.on_state_change)

    def left_mouse_double_click_event(self, position: Point2D):
        local_url = self.state().local_image_url
        if local_url:
            local_path = Path(local_url.path)
            if local_url.is_internal():
                local_path = media_store().path_for_internal_uri(local_url)

            if local_path.exists():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(local_path)))
                return

        super().left_mouse_double_click_event(position)

    def on_state_change(self, change: Change):
        state: ImageNoteViewState = change.last_state()

        if change.updated.color or change.updated.background_color:
            fg_col = QColor(*state.get_color().to_uint8_rgba_list())
            bg_col = QColor(*state.get_background_color().to_uint8_rgba_list())

            palette = self.palette()
            palette.setColor(self.backgroundRole(), bg_col)
            palette.setColor(self.foregroundRole(), fg_col)
            self.setPalette(palette)

        if change.updated.local_image_url or change.updated.preview_request_t:
            self.update_image_cache(state.image_url, state.local_image_url)
        if change.updated.geometry:
            self.setGeometry(QRect(*state.geometry))

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter()
        painter.begin(self)
        draw_link_decorations(self, painter)
        painter.end()

        super().paintEvent(event)
