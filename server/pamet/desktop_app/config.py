from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, NotRequired, TypedDict, cast

from fusion.util import get_new_id
from PySide6.QtCore import QCoreApplication, QStandardPaths

QCoreApplication.setApplicationName("pamet")


def _path_from_env_or_standard(
    env_var_name: str, standard_location: QStandardPaths.StandardLocation
) -> Path:
    env_path = os.environ.get(env_var_name)
    if env_path:
        return Path(env_path).expanduser()
    return Path(QStandardPaths.writableLocation(standard_location))


CONFIG_DIR = _path_from_env_or_standard(
    "PAMET_CONFIG_DIR", QStandardPaths.StandardLocation.AppConfigLocation
)
APP_DATA_DIR = _path_from_env_or_standard(
    "PAMET_APP_DATA_DIR", QStandardPaths.StandardLocation.AppLocalDataLocation
)
PROJECTS_DIR = APP_DATA_DIR / "projects"
USER_SETTINGS_DIR = CONFIG_DIR / "user"
REPO_PROPERTIES_JSON = "properties.json"


class UserDesktopSettingsData(TypedDict):
    id: str
    name: str
    projects: list[dict[str, Any]]


class RepoSettingsData(TypedDict):
    id: str
    title: str
    description: str
    created: str
    default_page_id: NotRequired[str | None]
    backups_enabled: bool
    backup_folder: str
    record_all_changes: bool
    semantic_search_enabled: bool


REPO_SETTINGS_DEFAULTS: RepoSettingsData = {
    "id": "",
    "title": "",
    "description": "",
    "created": "",
    "backups_enabled": True,
    "backup_folder": ".pamet/backups",
    "record_all_changes": False,
    "semantic_search_enabled": False,
}


class SettingsAdapter:
    def __init__(
        self,
        path: Path,
        defaults: Mapping[str, Any] | None = None,
    ):
        self.path = Path(path)
        self._defaults = dict(deepcopy(defaults or {}))

    def exists(self) -> bool:
        return self.path.exists()

    def read_raw(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        with self.path.open("r", encoding="utf-8") as file_obj:
            data = json.load(file_obj)
        if not isinstance(data, dict):
            raise TypeError(f"Expected dict settings in {self.path}")
        return cast(dict[str, Any], data)

    def get(self) -> dict[str, Any]:
        return {
            **dict(deepcopy(self._defaults)),
            **self.read_raw(),
        }

    def write(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(deepcopy(data), indent=4))


def user_settings_path() -> Path:
    return USER_SETTINGS_DIR / "settings.json"


def repo_settings_path(repo_path: Path) -> Path:
    return Path(repo_path) / ".pamet" / REPO_PROPERTIES_JSON


def get_repo_settings(repo_path: Path) -> RepoSettingsData:
    return cast(
        RepoSettingsData,
        SettingsAdapter(
            repo_settings_path(repo_path),
            defaults=REPO_SETTINGS_DEFAULTS,
        ).get(),
    )


def create_repo_settings(
    repo_path: Path,
    *,
    repo_id: str | None = None,
    title: str | None = None,
) -> RepoSettingsData:
    adapter = SettingsAdapter(
        repo_settings_path(repo_path),
        defaults=REPO_SETTINGS_DEFAULTS,
    )
    if adapter.exists():
        return cast(RepoSettingsData, adapter.get())

    settings = cast(RepoSettingsData, adapter.get())
    settings["id"] = repo_id or get_new_id()
    settings["title"] = title or Path(repo_path).name
    adapter.write(cast(dict[str, Any], settings))
    return settings


def save_repo_settings(
    repo_path: Path, repo_settings: RepoSettingsData | dict[str, Any]
):
    SettingsAdapter(
        repo_settings_path(repo_path),
        defaults=REPO_SETTINGS_DEFAULTS,
    ).write(cast(dict[str, Any], repo_settings))
