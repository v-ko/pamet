from PySide6.QtGui import QColor, QIcon
import pamet
from pamet.constants import SELECTION_OVERLAY_COLOR

trash_icon = QIcon(str(pamet.resource_path('icons/delete-bin-line.svg')))
link_icon = QIcon(str(pamet.resource_path('icons/link.svg')))
plus_icon = QIcon(str(pamet.resource_path('icons/plus.svg')))

selection_overlay_qcolor = QColor(
    *SELECTION_OVERLAY_COLOR.to_uint8_rgba_list())

config = get_config()
media_store = MediaStore(config['media_store_path'])
