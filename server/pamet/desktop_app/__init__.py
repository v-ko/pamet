from __future__ import annotations

from copy import copy
from pathlib import Path
from typing import Any, cast

from fusion.logging import get_logger
from pamet.constants import SELECTION_OVERLAY_COLOR
from pamet.desktop_app.app import DesktopApp
from pamet.desktop_app.config import (
    APP_DATA_DIR,
    CONFIG_DIR,
    PROJECTS_DIR,
    SettingsAdapter,
    UserDesktopSettingsData,
    user_settings_path,
)
from pamet.desktop_app.icon_cache import PametQtWidgetsCachedIcons
from pamet.services.backup import FSStorageBackupService
from pamet.services.media_store import MediaStore
from pamet.services.script_runner import ScriptRunner
from PySide6.QtGui import QColor

log = get_logger(__name__)

icons = PametQtWidgetsCachedIcons()

selection_overlay_qcolor = QColor(*SELECTION_OVERLAY_COLOR.to_uint8_rgba_list())

_app = None
_media_store = None
_backup_service = None

_default_note_font = None
script_runner = ScriptRunner()

_user_settings_adapter = SettingsAdapter(
    user_settings_path(),
)


def get_user_settings() -> UserDesktopSettingsData:
    return cast(UserDesktopSettingsData, _user_settings_adapter.get())


def save_user_settings(updated_config: UserDesktopSettingsData | dict[str, Any]):
    _user_settings_adapter.write(cast(dict[str, Any], updated_config))


def upsert_tracked_project(project_id: str, uri: str, user_id: str, title: str):
    settings = get_user_settings()
    if settings["id"] != user_id:
        raise ValueError(
            f"Cannot upsert tracked project for user '{user_id}' without initialized matching user settings"
        )

    projects = list(settings["projects"])
    project_data: dict[str, str] = {
        "id": project_id,
        "uri": uri,
        "title": title,
    }

    replaced = False
    for index, existing_project in enumerate(projects):
        if existing_project.get("id") == project_id:
            projects[index] = project_data
            replaced = True
            break

    if not replaced:
        projects.append(project_data)

    save_user_settings({**settings, "projects": projects})


def default_note_font():
    return copy(_default_note_font)


def set_default_note_font(new_default_note_font):
    global _default_note_font
    _default_note_font = new_default_note_font


def get_app() -> DesktopApp:
    return _app


def set_app(new_app):
    global _app
    _app = new_app


def media_store() -> MediaStore:
    if _media_store is None:
        raise ValueError("Media store not initialized")
    return _media_store


def set_media_store(new_media_store):
    global _media_store
    _media_store = new_media_store


def backup_service() -> FSStorageBackupService:
    if _backup_service is None:
        raise ValueError("Backup service not initialized")
    return _backup_service


def set_backup_service(backup_service_):
    global _backup_service
    _backup_service = backup_service_
