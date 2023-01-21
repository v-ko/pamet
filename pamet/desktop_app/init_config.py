from importlib import resources

from PySide6.QtGui import QFont, QFontDatabase
from fusion.extensions_loader import ExtensionsLoader
from fusion.platform.qt_widgets import configure_for_qt as fusion_config_qt
from pamet.desktop_app.config import UserDesktopSettings
from pamet.desktop_app.config import pamet_data_folder_path
from pamet.desktop_app.util import copy_script_templates
from pamet.services.media_store import MediaStore
from pamet import desktop_app
from fusion.logging import get_logger
from pamet.util import resource_path

log = get_logger(__name__)


def configure_for_qt(app):
    global _media_store, _default_note_font

    log.info(f'Using data folder: {pamet_data_folder_path}')
    desktop_app.set_app(app)
    fusion_config_qt(app)

    config: UserDesktopSettings = desktop_app.get_user_settings()
    if config.changes_present():
        desktop_app.save_user_settings(config)

    copy_script_templates()

    desktop_app.set_media_store(MediaStore(config.media_store_path))
    desktop_app.icons.load_all()

    _font_id = QFontDatabase.addApplicationFont(
        str(resource_path('fonts/OpenSans-VariableFont_wdth,wght.ttf')))
    _font_family = QFontDatabase.applicationFontFamilies(_font_id)[0]
    _default_note_font = QFont(_font_family)
    _default_note_font.setPointSizeF(14)
    desktop_app.set_default_note_font(_default_note_font)

    views_dir = resources.files('pamet') / 'views'
    pamet_root = views_dir.parent
    views_loader = ExtensionsLoader(pamet_root)
    views_loader.load_all_recursively(views_dir)
