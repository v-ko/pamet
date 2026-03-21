from __future__ import annotations

import threading
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname

from fusion.logging import get_logger
from pamet.desktop_app.config import create_repo_settings, repo_settings_path
from pamet.services.project_sync.project_folder_manager import ProjectFolderManager

log = get_logger(__name__)


class ProjectNotLoadedError(KeyError):
    pass


class DesktopStorageService:
    def __init__(self):
        self._project_folder_managers: dict[str, ProjectFolderManager] = {}
        self._lock = threading.RLock()
        self._vcs_lock = threading.RLock()

    def _path_from_file_uri(self, project_uri: str) -> Path:
        parsed_uri = urlparse(project_uri)
        if parsed_uri.scheme != "file":
            raise ValueError("Desktop project URI must use the file scheme")

        if parsed_uri.netloc:
            raise ValueError("Desktop project file URI must not use a remote host")

        repo_path = Path(url2pathname(unquote(parsed_uri.path)))
        if not repo_path.is_absolute():
            raise ValueError(
                "Desktop project file URI must resolve to an absolute path"
            )
        return repo_path

    def load_project(self, project_id: str, project_uri: str) -> None:
        with self._lock:
            if project_id in self._project_folder_managers:
                log.info(
                    "DesktopStorageService load_project is idempotent for %s",
                    project_id,
                )
                return
            if not project_uri.strip():
                raise ValueError("Desktop project load requires a file URI")
            repo_root = self._path_from_file_uri(project_uri.strip())
            if not repo_settings_path(repo_root).exists():
                create_repo_settings(
                    repo_root,
                    repo_id=project_id,
                    title=repo_root.name,
                )
            pfm = ProjectFolderManager(
                project_id=project_id,
                repo_root=repo_root,
                vcs_lock=self._vcs_lock,
            )
            pfm.load()
            self._project_folder_managers[project_id] = pfm
            log.info(
                "DesktopStorageService loaded ProjectFolderManager for %s",
                project_id,
            )

    def unload_project(self, project_id: str) -> None:
        with self._lock:
            pfm = self._project_folder_managers.pop(project_id, None)
            if pfm is None:
                return
            pfm.unload()
            log.info(
                "DesktopStorageService unloaded ProjectFolderManager for %s",
                project_id,
            )

    def project_folder_manager(self, project_id: str) -> ProjectFolderManager:
        with self._lock:
            pfm = self._project_folder_managers.get(project_id)
            if pfm is None:
                raise ProjectNotLoadedError(
                    f"No active project runtime for '{project_id}'"
                )
            return pfm
