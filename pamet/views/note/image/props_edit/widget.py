import hashlib
import io
from pathlib import Path
from PIL import Image

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QUrl, Qt
from PySide6.QtGui import QImage, QImageReader, QPixmap, QResizeEvent
from PySide6.QtNetwork import QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import QFileDialog, QWidget
from fusion.util.point2d import Point2D

from pamet.util.url import Url
from pamet.desktop_app import media_store
from pamet.model.card_note import CardNote
from pamet.model.image_note import ImageNote

from .ui_widget import Ui_ImagePropsWidget

MAX_IMAGE_SIZE_EDGE = 2048
MAX_IMAGE_SIZE_BYTES = 30 * 1000 * 1000


class ImagePropsWidget(QWidget):

    def __init__(self, parent):
        super().__init__(parent)

        self.edit_widget = parent

        # Locals
        self._image_preview = None

        self.ui = Ui_ImagePropsWidget()
        self.ui.setupUi(self)

        # Setup the image props widget
        if isinstance(self.edit_widget.edited_note, (ImageNote, CardNote)):
            # Set the url line edit text and then connect the handler (to avoid
            # triggering it beforehand)
            self.ui.urlLineEdit.setText(
                str(self.edit_widget.edited_note.image_url))

            # Setup the image from the local data if any
            local_url: Url = self.edit_widget.edited_note.local_image_url
            if local_url:
                path = local_url.path
                if local_url.is_internal():
                    path = media_store().path_for_internal_uri(local_url)

                image = QImage(path)
                if image.isNull():
                    self.update_image_note_and_preview(
                        error=f'Could not load local image at "{path}"')
                else:
                    self.update_image_note_and_preview(local_url, image)

            self.ui.urlLineEdit.textChanged.connect(
                self.handle_image_url_text_change)

            # If there's been a problem and the local url is missing - trigger
            # a download
            if self.edit_widget.edited_note.image_url and \
                    not self.edit_widget.edited_note.local_image_url:
                self.handle_image_url_text_change(
                    self.edit_widget.edited_note.image_url)

        # Image props connect
        self.ui.urlLineEdit.textChanged.connect(
            self.handle_image_url_text_change)
        self.ui.openFileButton.clicked.connect(
            self.handle_open_file_button_click)

    @property
    def _image_download_reply(self) -> QNetworkReply:
        return self.edit_widget._image_download_reply

    @_image_download_reply.setter
    def _image_download_reply(self, reply: QNetworkReply):
        self.edit_widget._image_download_reply = reply

    def handle_open_file_button_click(self):
        file_path, _ = QFileDialog.getOpenFileName()
        self.ui.urlLineEdit.setText(file_path)

    def resizeEvent(self, event: QResizeEvent) -> None:
        if self._image_preview and \
                self.edit_widget.edited_note.local_image_url:
            self.update_image_note_and_preview(
                local_image_url=self.edit_widget.edited_note.local_image_url,
                image=self._image_preview)
        return super().resizeEvent(event)

    def convert_image_with_pil(self, image_data: bytes):
        bytes_io = io.BytesIO(image_data)
        img_byte_arr = io.BytesIO()

        try:  # Probe if Pillow can handle the image
            pil_image = Image.open(bytes_io)  #@IgnoreException
            pil_image.save(img_byte_arr, 'png')
        except Exception:
            self.update_image_note_and_preview(
                error=('Could not read image with PIL.'))
            return

        return img_byte_arr.read()

    def update_image_note_and_preview(self,
                                      local_image_url: Url = None,
                                      image: QImage = None,
                                      md5sum: str = None,
                                      error: str = None):
        note = self.edit_widget.edited_note
        # Set the note image_url
        url_input = self.ui.urlLineEdit.text()
        note.image_url = url_input

        if error:
            if local_image_url or image or md5sum:
                raise Exception
            note.local_image_url = None
            self.ui.infoLabel.setText(error)
            self._image_preview = None
            return

        self._image_preview = image
        note.local_image_url = local_image_url
        note.image_size = Point2D(image.size().width(), image.size().height())
        note.image_md5 = md5sum

        w = self.ui.infoLabel.size().width()
        h = self.ui.infoLabel.size().height()
        pixmap = QPixmap.fromImage(image)
        pixmap = pixmap.scaled(w, h, Qt.KeepAspectRatio)
        self.ui.infoLabel.setPixmap(pixmap)

    def handle_image_url_text_change(self, new_text: str):
        if not new_text:
            self.update_image_note_and_preview(error='Image not specified')
            return

        url = Url(new_text)
        if url.scheme == 'file' or not url.scheme and Path(str(url)).exists():
            # Check if exists - if not - error
            url_path = Path(url.path)
            if not url_path.exists():
                self.update_image_note_and_preview(error='File does not exist')
                return
            # Check size before reading - if too big - error (for now)
            elif url_path.stat().st_size > MAX_IMAGE_SIZE_BYTES:
                self.update_image_note_and_preview(error='Image is too big')
                return

            # Read binary
            with open(url_path, 'rb') as image_file:
                image_data = image_file.read()

            # create buffer
            qbytearr = QByteArray(image_data)
            buffer = QBuffer(qbytearr)
            image_reader = QImageReader(buffer)

            # If Qt doesn't support the format (e.g. WebP)
            # try to convert it with Pillow to PNG
            if image_reader.format() not in \
                    image_reader.supportedImageFormats():

                image_data = self.convert_image_with_pil(image_data)
                bytearr = QByteArray(image_data)
                buffer = QBuffer(bytearr)
                image_reader = QImageReader(buffer)

            image = image_reader.read()
            if image.isNull():
                self.update_image_note_and_preview(
                    error='Could not load image')
                return

            # get md5
            md5sum = hashlib.md5(image_data).hexdigest()
            self.update_image_note_and_preview(local_image_url=url.path,
                                               image=image,
                                               md5sum=md5sum)
        elif url.is_internal():
            path = media_store().path_for_internal_uri(url)
            image = QImage(path)
            self.update_image_note_and_preview(path, image)
        elif url.has_web_schema():
            # Check if already downloaded - no. No such optimisations
            # (url <> path associations) present

            # Cancel previous download if any
            if self._image_download_reply:
                self._image_download_reply.abort()

            # Start downloading
            self._image_download_reply = self.edit_widget._network_am.get(
                QNetworkRequest(QUrl(str(url))))

            # Update label to mark downloading
            self.update_image_note_and_preview(error='Downloading...')

            # Done handler: remove reply, preview, save
            def on_complete():
                # This handler is called after on_error if one occurres
                if self._image_download_reply.error():
                    self.update_image_note_and_preview(
                        error=(f'Could not download image. Error:'
                               f' {self._image_download_reply.errorString()}'))
                    self._image_download_reply = None
                    return

                image_qbytearray = self._image_download_reply.readAll()
                image_data = image_qbytearray.data()
                if not image_data:
                    self.update_image_note_and_preview(error=(
                        'Download complete, but no image data to read.'))
                    return

                buffer = QBuffer(image_qbytearray)
                image_reader = QImageReader(buffer)
                img_format = image_reader.format().data().decode('utf-8')

                # If Qt doesn't support the format (e.g. WebP)
                # try to convert it with Pillow to PNG
                if image_reader.format() not in \
                        image_reader.supportedImageFormats():

                    image_data = self.convert_image_with_pil(image_data)
                    if not image_data:
                        return
                    buffer = QBuffer(QByteArray(image_data))
                    image_reader = QImageReader(buffer)

                image = image_reader.read()
                if image.isNull():
                    self.update_image_note_and_preview(
                        error=(f'Could not read image. Error:'
                               f' {image_reader.errorString()}'))
                    return

                # Check image size in bytes and scale down if needed
                if image.sizeInBytes() > MAX_IMAGE_SIZE_BYTES:
                    self.update_image_note_and_preview(
                        error='Image too big. Resizing before save.')
                    image = image.scaled(MAX_IMAGE_SIZE_EDGE,
                                         MAX_IMAGE_SIZE_EDGE,
                                         Qt.KeepAspectRatio)

                # Get format and if it's ok - save
                if not img_format:
                    self.update_image_note_and_preview(
                        error=f'Bad image format: "{img_format}"')
                    return

                blob = QByteArray()
                buffer = QBuffer(blob)
                buffer.open(QIODevice.WriteOnly)
                ok = image.save(buffer, img_format)
                if not ok:
                    self.update_image_note_and_preview(
                        error='Could not save image to buffer')
                    return

                local_url = media_store().save_blob(
                    self.edit_widget.state().page_id, blob, img_format, url)
                if not local_url:
                    self.update_image_note_and_preview(
                        error='Could not save image locally.')
                else:
                    self.update_image_note_and_preview(
                        error='Calculating md5sum.')
                    md5sum = hashlib.md5(image_data).hexdigest()

                    self.update_image_note_and_preview(
                        local_image_url=local_url, image=image, md5sum=md5sum)
                self._image_download_reply = None

            # def on_error(error_code: QNetworkReply.NetworkError):

            def on_progress(bytes_received: int, bytes_total: int):
                if bytes_total <= 0:
                    progress = f'{bytes_received / 1000:.2f}k/??'
                else:
                    progress = f'{bytes_received / bytes_total * 100:.2f}%'

                self.update_image_note_and_preview(
                    error=f'Download at {progress}')

            # Connect the handlers
            self._image_download_reply.finished.connect(on_complete)
            # self._image_download_reply.errorOccurred.connect(on_error)
            self._image_download_reply.downloadProgress.connect(on_progress)

        else:
            self.ui.infoLabel.setText('Url schema not recognized')
