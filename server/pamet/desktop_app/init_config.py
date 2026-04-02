from fusion.logging import get_logger
from fusion.platform.qt_widgets import configure_for_qt as fusion_config_qt
from PySide6.QtGui import QFont, QFontDatabase

from pamet import desktop_app
from pamet.desktop_app.config import APP_DATA_DIR, CONFIG_DIR
from pamet.util import resource_path

log = get_logger(__name__)


def configure_for_qt(app):
    global _default_note_font

    log.info(f"Using config folder: {CONFIG_DIR}")
    log.info(f"Using app data folder: {APP_DATA_DIR}")
    desktop_app.set_app(app)
    fusion_config_qt(app)

    desktop_app.icons.load_all()

    _font_id = QFontDatabase.addApplicationFont(
        str(resource_path("fonts/OpenSans-VariableFont_wdth,wght.ttf"))
    )
    _font_family = QFontDatabase.applicationFontFamilies(_font_id)[0]
    _default_note_font = QFont(_font_family)
    _default_note_font.setPointSizeF(14)
    desktop_app.set_default_note_font(_default_note_font)
