from copy import copy
import json
from pathlib import Path
from PySide6.QtGui import QColor

from fusion.logging import get_logger

from pamet.constants import SELECTION_OVERLAY_COLOR
from pamet.desktop_app.config import RepoSettings, UserDesktopSettings
from pamet.desktop_app.icon_cache import PametQtWidgetsCachedIcons
from pamet.services.script_runner import ScriptRunner
from pamet.desktop_app.config import pamet_data_folder_path

log = get_logger(__name__)

SETTINGS_JSON = 'settings.json'

icons = PametQtWidgetsCachedIcons()

selection_overlay_qcolor = QColor(
    *SELECTION_OVERLAY_COLOR.to_uint8_rgba_list())

_media_store = None
_default_note_font = None
_app = None
script_runner = ScriptRunner()


def user_settings_path() -> Path:
    return pamet_data_folder_path / SETTINGS_JSON


def repo_settings_path(repo_path: Path) -> Path:
    return repo_path / '.pamet' / SETTINGS_JSON


# Config handling
def get_user_settings() -> UserDesktopSettings:
    settings_path = user_settings_path()
    if not settings_path.exists():
        return UserDesktopSettings()

    with open(settings_path) as settings_file:
        config_dict = json.load(settings_file)
        return UserDesktopSettings.load(config_dict)


def save_user_settings(updated_config: UserDesktopSettings):
    config_str = json.dumps(updated_config.asdict(),
                            indent=4,
                            ensure_ascii=False)
    config_path = user_settings_path()
    config_path.write_text(config_str)


def get_repo_settings(repo_path: Path) -> RepoSettings:
    config_path = repo_settings_path(repo_path)
    if not config_path.exists():
        return RepoSettings(repo_path=repo_path)

    with open(config_path) as config_file:
        config_dict = json.load(config_file)
        dict_on_load = copy(config_dict)
        settings_id = config_dict.pop('id')
        settings = RepoSettings(id=settings_id, repo_path=repo_path)
        settings.replace_silent(**config_dict)
        settings._dict_on_load = dict_on_load
        return settings


def save_repo_settings(repo_settings: RepoSettings):
    config_str = json.dumps(repo_settings.asdict(),
                            indent=4,
                            ensure_ascii=False)
    config_path = repo_settings_path(repo_settings.repo_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(config_str)


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


def get_app():
    return _app


def set_app(new_app):
    global _app
    _app = new_app
