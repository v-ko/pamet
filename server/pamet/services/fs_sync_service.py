from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, Set

from fusion.logging import get_logger
from pamet.storage.migrations.manager import V5_FILE_EXT, MigrationManager
from PySide6.QtCore import QFileSystemWatcher

log = get_logger(__name__)

if TYPE_CHECKING:
    from pamet.services.project_sync.project_folder_manager import ProjectFolderManager


_IGNORED_DIRS = {
    ".pamet",
    "__migration_backup_v2_to_v3__",
    "__migration_backup_v3_to_v4__",
    "__migration_backup_v4_to_v5__",
}


class FileSystemSyncService:
    """
    Project-folder filesystem service.

    Responsibilities:
    - run project-folder migrations when requested by the ProjectFolderManager
    - watch filesystem changes under the project root
    - own bootstrap-integrity / FS-delta helpers
    """

    def __init__(self, project_folder_manager: "ProjectFolderManager"):
        self.project_folder_manager = project_folder_manager
        self._watcher: QFileSystemWatcher | None = None
        self.migration_manager = MigrationManager(self.repo_root)

    @property
    def repo_root(self) -> Path:
        return self.project_folder_manager.repo_root

    def _iter_canvas_page_paths(self) -> Iterable[Path]:
        for dirpath, dirnames, filenames in os.walk(self.repo_root):
            dirnames[:] = [dirname for dirname in dirnames if dirname not in _IGNORED_DIRS]
            for fname in filenames:
                if fname.endswith(V5_FILE_EXT):
                    yield Path(dirpath) / fname

    def compute_bootstrap_delta(self) -> dict | None:
        raise NotImplementedError(
            "FileSystemSyncService.compute_bootstrap_delta() is not implemented yet."
        )

    def get_pending_delta(self) -> dict | None:
        raise NotImplementedError(
            "FileSystemSyncService.get_pending_delta() is not implemented yet."
        )

    def _collect_dirs_recursive(self) -> list[str]:
        paths: list[str] = [str(self.repo_root)]
        for dirpath, dirnames, _filenames in os.walk(self.repo_root):
            dirnames[:] = [dirname for dirname in dirnames if dirname not in _IGNORED_DIRS]
            paths.extend(str(Path(dirpath) / dirname) for dirname in dirnames)
        return paths

    def _ensure_subdirs_watched(self) -> None:
        if self._watcher is None:
            return
        current: Set[str] = set(self._watcher.directories())
        needed = set(self._collect_dirs_recursive())
        new_dirs = list(needed - current)
        if new_dirs:
            self._watcher.addPaths(new_dirs)

    def start_watching(self) -> None:
        if self._watcher is not None:
            return
        self._watcher = QFileSystemWatcher()
        dirs = self._collect_dirs_recursive()
        if dirs:
            self._watcher.addPaths(dirs)
        self._watcher.directoryChanged.connect(self._on_directory_changed)  # type: ignore
        self._watcher.fileChanged.connect(self._on_file_changed)  # type: ignore
        log.info(
            "[FileSystemSyncService] Watching %s directories under %s",
            len(self._watcher.directories()),
            self.repo_root,
        )

    def stop_watching(self) -> None:
        if self._watcher is None:
            return
        try:
            dirs = self._watcher.directories()
            files = self._watcher.files()
            if dirs:
                self._watcher.removePaths(dirs)
            if files:
                self._watcher.removePaths(files)
        finally:
            self._watcher = None

    def _on_directory_changed(self, path: str) -> None:
        log.info("[FileSystemSyncService] Directory changed: %s", path)
        self._ensure_subdirs_watched()

    def _on_file_changed(self, path: str) -> None:
        log.info("[FileSystemSyncService] File changed: %s", path)

    def index_folder(self) -> int:
        count = 0
        for _ in self._iter_canvas_page_paths():
            count += 1
        log.info("Indexed %s canvas page file(s) in %s", count, self.repo_root)
        return count
