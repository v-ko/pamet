from __future__ import annotations

import threading
from pathlib import Path

from fusion.logging import get_logger
from fusion.storage.in_memory_store import InMemoryStore
from fusion.storage.store_sync_service import StoreSyncService

from pamet.desktop_app.config import create_repo_settings, repo_settings_path
from pamet.services.config_file_manager import ConfigFileManager, DSSStatus
from pamet.services.project_sync.project_folder_manager import ProjectFolderManager

log = get_logger(__name__)


class ProjectNotLoadedError(KeyError):
    pass


class DesktopStorageService:
    def __init__(self):
        self._project_folder_managers: dict[str, ProjectFolderManager] = {}
        self._lock = threading.RLock()

        # Status object — services write errors here, exposed via /status
        self.status: DSSStatus = {"errors": {}}
        self.status["errors"]["config_file_manager"] = {}

        # Config store: holds UserSettings, MiscProperties, ProjectProperties
        self._config_store = InMemoryStore()
        self._config_file_manager = ConfigFileManager(
            store=self._config_store,
            resolve_project_path=self._resolve_project_path,
            status_errors=self.status["errors"]["config_file_manager"],
        )
        self._config_sync_service = StoreSyncService(self._config_store)

        # Wire persistence: store changes → file manager
        self._config_store.on_changes = self._config_file_manager.on_changes

        # Load existing config from disk
        self._config_file_manager.load_app_config(self._config_store)

    @property
    def config_sync_service(self) -> StoreSyncService:
        return self._config_sync_service

    @property
    def config_store(self) -> InMemoryStore:
        return self._config_store

    def _resolve_project_path(self, project_id: str) -> Path | None:
        """Resolve a project ID to its repo root path."""
        with self._lock:
            pfm = self._project_folder_managers.get(project_id)
            if pfm is not None:
                return pfm.repo_root
        return None

    def load_project(self, project_id: str, repo_root: Path) -> None:
        with self._lock:
            if project_id in self._project_folder_managers:
                log.info(
                    "DesktopStorageService load_project is idempotent for %s",
                    project_id,
                )
                return
            if not repo_root.is_absolute():
                raise ValueError("repo_root must be an absolute path")

            if not repo_settings_path(repo_root).exists():
                create_repo_settings(
                    repo_root,
                    repo_id=project_id,
                    title=repo_root.name,
                )

            pfm = ProjectFolderManager(
                project_id=project_id,
                repo_root=repo_root,
            )
            pfm.load()
            self._project_folder_managers[project_id] = pfm

            # Load project properties into the config store
            self._config_file_manager.load_project_properties(
                self._config_store,
                project_id,
            )

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
