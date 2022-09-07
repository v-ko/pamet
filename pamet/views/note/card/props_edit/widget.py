from PySide6.QtCore import QSize, QUrl
from PySide6.QtNetwork import QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import QTextEdit, QWidget

import pamet
from pamet.util.url import Url
from .ui_widget import Ui_TextEditPropsWidget

TEXT_EDIT_MIN_SIZE = 30


class FixedTextEdit(QTextEdit):
    """The default QTextEdit implementation has an inflexible (borderline
    buggy) size constraints, which cannot be overwriteen in any other way."""

    def minimumSizeHint(self) -> QSize:
        return QSize(TEXT_EDIT_MIN_SIZE, TEXT_EDIT_MIN_SIZE)

    def sizeHint(self) -> QSize:
        return QSize(TEXT_EDIT_MIN_SIZE, TEXT_EDIT_MIN_SIZE)


class TextEditPropsWidget(QWidget):

    def __init__(self, parent):
        super().__init__(parent)
        self.edit_widget = parent

        self.ui = Ui_TextEditPropsWidget()
        self.ui.setupUi(self)
        layout = self.layout()
        self.text_edit = FixedTextEdit(self)
        layout.addWidget(self.text_edit)
        self.setLayout(layout)

        # Connect stuff
        self.ui.getTitleButton.clicked.connect(self._get_title)
        self.text_edit.textChanged.connect(self.on_text_change)

    @property
    def _image_download_reply(self) -> QNetworkReply:
        return self.edit_widget._image_download_reply

    @_image_download_reply.setter
    def _image_download_reply(self, reply: QNetworkReply):
        self.edit_widget._image_download_reply = reply

    def on_text_change(self):
        new_text = self.text_edit.toPlainText().strip()
        self.edit_widget.edited_note.text = new_text

    def _get_title(self):
        edited_note = self.edit_widget.edited_note
        url: Url = edited_note.url
        page = pamet.page(url.get_page_id())

        if page:
            self.text_edit.setText(page.name)
        elif url.is_external():
            if not url.scheme:
                url_str = 'https://' + str(url)
            else:
                url_str = str(url)
            self._image_download_reply = self.edit_widget._network_am.get(
                QNetworkRequest(QUrl(url_str)))

            self.ui.downloadInfoLabel.show()

            # Done handler: remove reply, preview, save
            def on_complete():
                # This handler is called after on_error if one occurres
                if self._image_download_reply.error():
                    self.ui.downloadInfoLabel.setText('Download error')
                    return
                html = self._image_download_reply.readAll().toStdString()
                title = html[html.find('<title>') + 7:html.find('</title>')]
                self.text_edit.setText(title)
                self.ui.downloadInfoLabel.hide()

            def on_progress(bytes_received: int, bytes_total: int):
                if bytes_total <= 0:
                    progress = f'{bytes_received / 1000:.2f}k/??'
                else:
                    progress = f'{bytes_received / bytes_total * 100:.2f}%'

                self.ui.downloadInfoLabel.setText(f'Download at {progress}')

            # Connect the handlers
            self._image_download_reply.finished.connect(on_complete)
            self._image_download_reply.downloadProgress.connect(on_progress)
