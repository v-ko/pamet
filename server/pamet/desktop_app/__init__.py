from __future__ import annotations

from copy import copy
from typing import Any, cast

from sivkit.logging import get_logger

from pamet.desktop_app.app import DesktopApp
from pamet.desktop_app.config import (
    SettingsAdapter,
    UserDesktopSettingsData,
    user_settings_path,
)
from pamet.desktop_app.icon_cache import PametQtWidgetsCachedIcons

log = get_logger(__name__)

icons = PametQtWidgetsCachedIcons()

_app = None
_default_note_font = None

_user_settings_adapter = SettingsAdapter(
    user_settings_path(),
)


def get_user_settings() -> UserDesktopSettingsData:
    return cast(UserDesktopSettingsData, _user_settings_adapter.get())


def save_user_settings(updated_config: UserDesktopSettingsData | dict[str, Any]):
    _user_settings_adapter.write(cast(dict[str, Any], updated_config))


def upsert_tracked_project(project_id: str, uri: str, title: str):
    settings = get_user_settings()
    if not settings:
        raise Exception("User settings not found when trying to upsert tracked project")

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
    if _app is None:
        raise Exception("App not set")
    return _app


def set_app(new_app):
    global _app
    _app = new_app
