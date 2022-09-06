from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap, QResizeEvent
from PySide6.QtWidgets import QLabel
from pathlib import Path

from pamet.desktop_app import media_store
from pamet.util.url import Url


class ImageLabel(QLabel):

    def __init__(self, parent):
        QLabel.__init__(self, parent)
        self._image = None
        self._old_size = self.size()

        self.setWordWrap(True)
        self.setAlignment(Qt.AlignCenter)

    def image(self) -> QImage:
        return self._image

    def update_image_cache(self, url: Url, local_url: Url):
        if local_url:
            local_path = Path(local_url.path)
            if local_url.is_internal():
                local_path = media_store().path_for_internal_uri(local_url)

            if not local_path.exists():
                self.setText(f'Local path missing: {local_path}')
            else:
                self._image = QImage(local_path)
                if self._image.isNull():
                    self.setText(f'Could not load the image at {local_path}')
                    self._image = None
                    return
                self.update_pixmap()

        else:
            if not url:
                self.setText('No image chosen')
            else:
                self.setText(
                    'Image was not properly downloaded. Edit it to try again.')

    def update_pixmap(self):
        if not self._image:
            return
        scaled_image = self._image.scaled(self.size(), Qt.KeepAspectRatio,
                                          Qt.SmoothTransformation)
        self.setPixmap(QPixmap.fromImage(scaled_image))

    def resizeEvent(self, event: QResizeEvent):
        new_size = self.rect().size()
        if new_size != self._old_size:
            self._old_size = new_size
            self.update_pixmap()
