from copy import copy
from PySide6.QtGui import QColor

import fusion
from fusion.logging import get_logger

from pamet.constants import SELECTION_OVERLAY_COLOR
from pamet.desktop_app.config import DesktopConfig
from pamet.desktop_app.icon_cache import PametQtWidgetsCachedIcons
from pamet.services.script_runner import ScriptRunner

log = get_logger(__name__)

icons = PametQtWidgetsCachedIcons()

selection_overlay_qcolor = QColor(
    *SELECTION_OVERLAY_COLOR.to_uint8_rgba_list())

_media_store = None
_default_note_font = None
_app = None
script_runner = ScriptRunner()


# Config handling
def get_config() -> DesktopConfig:
    config_dict = fusion.gui.util_provider().get_config()
    return DesktopConfig.load(config_dict)


def save_config(config: DesktopConfig):
    fusion.gui.util_provider().set_config(config.asdict())


def media_store():
    return _media_store


def set_media_store(new_media_store):
    global _media_store
    _media_store = new_media_store


def default_note_font():
    return copy(_default_note_font)


def set_default_note_font(new_default_note_font):
    global _default_note_font
    _default_note_font = new_default_note_font


def app():
    return _app


def set_app(new_app):
    global _app
    _app = new_app
