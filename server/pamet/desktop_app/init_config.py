from importlib import resources

from fusion.extensions_loader import ExtensionsLoader
from fusion.logging import get_logger
from fusion.platform.qt_widgets import configure_for_qt as fusion_config_qt
from pamet.util import resource_path
from PySide6.QtGui import QFont, QFontDatabase

from pamet import desktop_app

log = get_logger(__name__)


def configure_for_qt(app):
    global _media_store, _default_note_font

    log.info(f"Using config folder: {desktop_app.CONFIG_DIR}")
    log.info(f"Using app data folder: {desktop_app.APP_DATA_DIR}")
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

    views_dir = resources.files("pamet") / "views"
    pamet_root = views_dir.parent
    views_loader = ExtensionsLoader(pamet_root)
    views_loader.load_all_recursively(views_dir)
