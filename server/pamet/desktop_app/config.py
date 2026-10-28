from __future__ import annotations

import json
import os
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QStandardPaths
from sivkit.libs.model import dump_to_dict, load_from_dict
from sivkit.util import get_new_id

from pamet.model.config import ProjectProperties

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


def user_settings_path() -> Path:
    return USER_SETTINGS_DIR / "settings.json"


def repo_settings_path(repo_path: Path) -> Path:
    return Path(repo_path) / ".pamet" / REPO_PROPERTIES_JSON


def get_repo_settings(
    repo_path: Path, project_id: str | None = None
) -> ProjectProperties:
    """Read the project settings entity; missing fields use model defaults."""
    path = repo_settings_path(repo_path)
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected dict settings in {path}")
    # Always use the canonical project_id when supplied by DSS, not whatever
    # "id" the on-disk V4 file might contain. Otherwise use the stored project_id.
    project_id = project_id if project_id is not None else data.get("project_id", "")
    # The on-disk file may be raw project data (no type_name) from migrations
    # or older code paths. Inject entity metadata so load_from_dict can
    # deserialise it as a ProjectProperties entity.
    data.update(
        type_name="ProjectProperties",
        parent_id="",
        id=ProjectProperties.id_for_project(project_id),
        project_id=project_id,
    )
    return load_from_dict(data)


def create_repo_settings(
    repo_path: Path,
    *,
    repo_id: str | None = None,
    title: str | None = None,
) -> ProjectProperties:
    path = repo_settings_path(repo_path)
    if path.exists():
        return get_repo_settings(repo_path, repo_id)
    project_id = repo_id or get_new_id()
    settings = ProjectProperties(
        id=ProjectProperties.id_for_project(project_id),
        project_id=project_id,
        title=title or Path(repo_path).name,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    data = dump_to_dict(settings)
    data.pop("parent_id", None)
    path.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")
    return settings
