from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from pamet.desktop_app.config import get_repo_settings, save_repo_settings
from pamet.services.fs_sync_service import FileSystemSyncService
from pamet.services.project_sync.vcs_db_adapter import VcsDbAdapter

import pamet

if TYPE_CHECKING:
    from pamet.services.media_backend import BlobStorageAdapter


class ProjectFolderManager:
    """
    Per-project desktop runtime owner.

    Current split:
    - filesystem watching / migration / bootstrap-delta helpers live in
      FileSystemSyncService
    - repo-facing VCS methods live here
    """

    def __init__(self, project_id: str, repo_root: Path, vcs_lock: Any | None = None):
        self.project_id = project_id
        self.repo_root = Path(repo_root)
        self.vcs_lock = vcs_lock
        self.vcs_db_adapter = VcsDbAdapter(self.repo_root)
        self.fs_sync_service = FileSystemSyncService(self)
        self._blob_storage_adapter: BlobStorageAdapter | None = None

    def load(self) -> None:
        self.fs_sync_service.migration_manager.do_all_migrations()
        self.fs_sync_service.index_folder()
        self.fs_sync_service.start_watching()

    def unload(self) -> None:
        self.fs_sync_service.stop_watching()

    def get_commit_graph(self, branch_name: str) -> dict[str, Any]:
        if self.vcs_lock is None:
            self.vcs_db_adapter.ensure_branch(branch_name)
            return self.vcs_db_adapter.get_commit_graph()
        with self.vcs_lock:
            self.vcs_db_adapter.ensure_branch(branch_name)
            return self.vcs_db_adapter.get_commit_graph()

    def get_commits(self, ids: list[str], branch_name: str) -> list[dict[str, Any]]:
        _ = branch_name
        if self.vcs_lock is None:
            return self.vcs_db_adapter.get_commits(ids)
        with self.vcs_lock:
            return self.vcs_db_adapter.get_commits(ids)

    def apply_repo_update(self, update_data: dict[str, Any]) -> None:
        if self.vcs_lock is None:
            self.vcs_db_adapter.apply_repo_update(update_data)
            return
        with self.vcs_lock:
            self.vcs_db_adapter.apply_repo_update(update_data)

    def get_project_properties(self) -> dict[str, Any]:
        repo_settings = get_repo_settings(self.repo_root)
        result: dict[str, Any] = {
            "id": self.project_id,
            "title": repo_settings["title"],
            "description": repo_settings["description"],
            "created": repo_settings["created"],
        }
        default_page_id = repo_settings.get("default_page_id")
        if default_page_id is not None:
            result["defaultPageId"] = default_page_id
        return result

    def set_project_properties(self, project_properties: dict[str, Any]) -> None:
        repo_settings = get_repo_settings(self.repo_root)
        repo_settings["title"] = project_properties.get("title", repo_settings["title"])
        repo_settings["description"] = project_properties.get(
            "description",
            repo_settings["description"],
        )
        repo_settings["created"] = project_properties.get(
            "created", repo_settings["created"]
        )
        if "defaultPageId" in project_properties:
            repo_settings["default_page_id"] = project_properties["defaultPageId"]
        save_repo_settings(self.repo_root, repo_settings)

    def get_pending_delta(self) -> dict[str, Any] | None:
        return self.fs_sync_service.get_pending_delta()

    @property
    def blob_storage_adapter(self):
        if self._blob_storage_adapter is None:
            from pamet.services.media_backend import BlobStorageAdapter

            self._blob_storage_adapter = BlobStorageAdapter(
                self.repo_root,
                project_manager=self,
            )
        return self._blob_storage_adapter
