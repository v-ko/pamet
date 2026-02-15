from importlib import resources

from fusion.extensions_loader import ExtensionsLoader
from fusion.logging import get_logger
from fusion.platform.qt_widgets import configure_for_qt as fusion_config_qt
from pamet.desktop_app.config import DEFAULT_DATA_FOLDER_PATH, UserDesktopSettings
from pamet.desktop_app.util import copy_script_templates
from pamet.util import resource_path
from PySide6.QtGui import QFont, QFontDatabase

from pamet import desktop_app

log = get_logger(__name__)


def configure_for_qt(app):
    global _media_store, _default_note_font

    log.info(f"Using data folder: {DEFAULT_DATA_FOLDER_PATH}")
    desktop_app.set_app(app)
    fusion_config_qt(app)

    config: UserDesktopSettings = desktop_app.get_user_settings()
    if config.changes_present():
        desktop_app.save_user_settings(config)

    copy_script_templates()

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
