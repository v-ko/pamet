from PySide6.QtGui import QColor, QIcon
import pamet
from pamet.constants import SELECTION_OVERLAY_COLOR
from pamet.services.media_store import MediaStore
from pamet.desktop_app.config import get_config

trash_icon = QIcon(str(pamet.resource_path('icons/delete-bin-line.svg')))
link_icon = QIcon(str(pamet.resource_path('icons/link.svg')))
plus_icon = QIcon(str(pamet.resource_path('icons/plus.svg')))
text_icon = QIcon(str(pamet.resource_path('icons/text.svg')))
image_icon = QIcon(str(pamet.resource_path('icons/image-line.svg')))

selection_overlay_qcolor = QColor(
    *SELECTION_OVERLAY_COLOR.to_uint8_rgba_list())

config = get_config()
media_store = MediaStore(config['media_store_path'])
