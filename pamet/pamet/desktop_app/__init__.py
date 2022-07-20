from PySide6.QtGui import QColor, QIcon
import misli
from misli.gui.utils.qt_widgets.provider import QtWidgetsUtilProvider
from misli.logging import get_logger
import pamet
from pamet.constants import SELECTION_OVERLAY_COLOR
from pamet.services.media_store import MediaStore
from .config import pamet_data_folder_path

log = get_logger(__name__)


class PametQtWidgetsCachedIcons:
    trash: QIcon = None
    link: QIcon = None
    plus: QIcon = None
    text: QIcon = None
    image: QIcon = None

    def load_all(self):
        self.trash = QIcon(
            str(pamet.resource_path('icons/delete-bin-line.svg')))
        self.link = QIcon(str(pamet.resource_path('icons/link.svg')))
        self.plus = QIcon(str(pamet.resource_path('icons/plus.svg')))
        self.text = QIcon(str(pamet.resource_path('icons/text.svg')))
        self.image = QIcon(str(pamet.resource_path('icons/image-line.svg')))


icons = PametQtWidgetsCachedIcons()

selection_overlay_qcolor = QColor(
    *SELECTION_OVERLAY_COLOR.to_uint8_rgba_list())

_media_store = None


def media_store():
    return _media_store


def configure_for_qt():
    global _media_store

    # Force view registration (should be handled by the ExtensionManager)
    from pamet.views.map_page.widget import MapPageWidget
    from pamet.views.note.text.widget import TextNoteWidget
    from pamet.views.note.text.edit_widget import CardNoteEditWidget
    from pamet.views.note.image.widget import ImageNoteWidget

    misli.configure_for_qt()

    log.info(f'Using data folder: {pamet_data_folder_path}')
    util_provider = QtWidgetsUtilProvider(pamet_data_folder_path)
    misli.gui.set_util_provider(util_provider)

    import pamet
    config = pamet.get_config()
    _media_store = MediaStore(config.media_store_path)
    icons.load_all()
