from __future__ import annotations

import logging
from copy import copy

from pamet.desktop_app.app import DesktopApp
from pamet.desktop_app.config import user_settings_path
from pamet.desktop_app.icon_cache import PametQtWidgetsCachedIcons

log = logging.getLogger(__name__)

icons = PametQtWidgetsCachedIcons()

_app = None
_default_note_font = None


def default_note_font():
    return copy(_default_note_font)


def set_default_note_font(new_default_note_font):
    global _default_note_font
    _default_note_font = new_default_note_font


def get_app() -> DesktopApp:
    if _app is None:
        raise Exception("App not set")
    return _app


def set_app(new_app):
    global _app
    _app = new_app
