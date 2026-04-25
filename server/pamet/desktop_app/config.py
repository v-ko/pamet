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


PAMET_CONFIG_DIR = _path_from_env_or_standard(
    "PAMET_CONFIG_DIR", QStandardPaths.StandardLocation.AppConfigLocation
)
PAMET_APP_DATA_DIR = _path_from_env_or_standard(
    "PAMET_APP_DATA_DIR", QStandardPaths.StandardLocation.AppLocalDataLocation
)
PROJECTS_DIR = PAMET_APP_DATA_DIR / "projects"
USER_SETTINGS_DIR = PAMET_CONFIG_DIR / "user"
REPO_PROPERTIES_JSON = "properties.json"


# Bundled web-app build directory (vite outDir for BUILD_MODE=desktop).
# Lives inside the package so it ships with the wheel.
_BUNDLED_WEB_APP_DIST = Path(__file__).resolve().parent / "_web_app_dist"


def web_app_static_build_path() -> Path:
    """Locate the built desktop web-app to be served by DesktopServer.

    Resolution order:
      1. ``$PAMET_WEB_APP_DIST`` if set (escape hatch for ad-hoc builds).
      2. The package-bundled ``_web_app_dist`` directory populated by
         ``npm run build:desktop``.

    Raises:
        RuntimeError: if the resolved directory does not contain an
            ``index.html`` (no build, partial build, or wrong path).
    """
    env_override = os.environ.get("PAMET_WEB_APP_DIST")
    candidate = (
        Path(env_override).expanduser() if env_override else _BUNDLED_WEB_APP_DIST
    )

    if not (candidate / "index.html").exists():
        source = (
            f"PAMET_WEB_APP_DIST={env_override}"
            if env_override
            else f"bundled path {candidate}"
        )
        raise RuntimeError(
            f"No web-app build found at {source}. Run `npm run build:desktop` "
            "in the pamet repo, or set PAMET_FRONTEND_DEV_SERVER / "
            "--use-frontend-server to use a dev server instead."
        )

    return candidate


class UserDesktopSettingsData(TypedDict):
    id: str
    name: str
    projects: list[dict[str, Any]]


# glob pattern → enabled (same notation as VS Code "files.exclude")
RepoSettingsData = TypedDict(
    "RepoSettingsData",
    {
        "id": str,
        "title": str,
        "description": str,
        "created": str,
        "home_page_id": NotRequired[str | None],
        "files.exclude": NotRequired[dict[str, bool]],
    },
)

REPO_SETTINGS_DEFAULTS: RepoSettingsData = {
    "id": "",
    "title": "",
    "description": "",
    "created": "",
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
