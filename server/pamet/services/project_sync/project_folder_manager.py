from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from fusion.logging import get_logger

from pamet.desktop_app.config import get_repo_settings, save_repo_settings
from pamet.services.fs_sync_service import _FILE_ITEM_TYPE_NAMES, FileSystemSyncService

log = get_logger(__name__)

from pamet.services.file_storage_adapter import FileStorageAdapter


class ProjectFolderManager:
    """
    Per-project desktop runtime owner.

    Owns an in-memory entity store populated from .canvas files on load().
    VCS persistence now lives in frontend IndexedDB — backend is a
    filesystem bridge only.
    """

    def __init__(self, project_id: str, repo_root: Path):
        self.project_id = project_id
        self.repo_root = Path(repo_root)
        self.fs_sync_service = FileSystemSyncService(self)
        self._blob_storage_adapter: FileStorageAdapter | None = None
        self._entity_store: dict[str, dict[str, Any]] = {}
        self._last_snapshot_hash: str | None = None

    def load(self) -> None:
        self.fs_sync_service.migration_manager.do_all_migrations()
        self._entity_store = self.fs_sync_service.read_all_entities()
        log.info(
            "Loaded %d entities for project %s",
            len(self._entity_store),
            self.project_id,
        )
        self.fs_sync_service.start_watching()

    def unload(self) -> None:
        self.fs_sync_service.stop_watching()
        self._entity_store.clear()

    def find_entities(
        self, filter: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Return entities from the in-memory store.

        If filter is None or empty, returns all entities.
        Any non-empty filter raises NotImplementedError for now.
        """
        if filter:
            raise NotImplementedError("Filtered find is not implemented")
        return list(self._entity_store.values())

    # -- Delta application (user edits → filesystem) --------------------------

    def apply_delta(
        self, delta_data: dict[str, Any], snapshot_hash: str | None = None
    ) -> None:
        """Apply a DeltaData dict to the in-memory store and write affected pages."""
        affected_page_ids: set[str] = set()
        deleted_page_ids: set[str] = set()

        for entity_id, change_data in delta_data.items():
            _eid, reverse_component, forward_component = change_data
            is_create = forward_component and not reverse_component
            is_delete = reverse_component and not forward_component
            is_update = forward_component and reverse_component

            if is_create:
                self._entity_store[entity_id] = dict(forward_component)
                page_id = self._resolve_page_id(entity_id, forward_component)
                if page_id:
                    affected_page_ids.add(page_id)

            elif is_delete:
                removed = self._entity_store.pop(entity_id, None)
                page_id = self._resolve_page_id(entity_id, removed or reverse_component)
                if page_id:
                    # Check if the page itself was deleted
                    if (removed or reverse_component).get("type_name") == "Page":
                        deleted_page_ids.add(entity_id)
                    else:
                        affected_page_ids.add(page_id)

            elif is_update:
                existing = self._entity_store.get(entity_id)
                if existing is None:
                    log.warning(
                        "Update for unknown entity %s, treating as create", entity_id
                    )
                    existing = {}
                    self._entity_store[entity_id] = existing
                existing.update(forward_component)
                page_id = self._resolve_page_id(entity_id, existing)
                if page_id:
                    affected_page_ids.add(page_id)

        # Write affected pages to disk (exclude deleted ones)
        affected_page_ids -= deleted_page_ids
        for page_id in affected_page_ids:
            self._write_page_to_disk(page_id)

        # Delete removed pages from disk
        for page_id in deleted_page_ids:
            self.fs_sync_service.delete_page_canvas_file(page_id)

        if snapshot_hash is not None:
            self._last_snapshot_hash = snapshot_hash

        log.info(
            "Applied delta: %d changes, %d pages written, %d pages deleted",
            len(delta_data),
            len(affected_page_ids),
            len(deleted_page_ids),
        )

    def _resolve_page_id(
        self, entity_id: str, entity_dict: dict[str, Any]
    ) -> str | None:
        """Return the page id for the given entity (itself if it's a Page, else parent_id)."""
        type_name = entity_dict.get("type_name", "")
        if type_name == "Page":
            return entity_id
        return entity_dict.get("parent_id")

    def _write_page_to_disk(self, page_id: str) -> None:
        """Assemble a page's data from the entity store and write it as a .canvas file."""
        page_dict = self._entity_store.get(page_id)
        if page_dict is None:
            log.warning("Cannot write page %s: not found in entity store", page_id)
            return

        notes: list[dict[str, Any]] = []
        arrows: list[dict[str, Any]] = []
        file_items: list[dict[str, Any]] = []
        for eid, entity in self._entity_store.items():
            if entity.get("parent_id") != page_id:
                continue
            type_name = entity.get("type_name", "")
            if type_name == "Arrow":
                arrows.append(entity)
            elif type_name in _FILE_ITEM_TYPE_NAMES:
                file_items.append(entity)
            else:
                notes.append(entity)

        self.fs_sync_service.write_page_canvas_file(
            page_id, page_dict, notes, arrows, file_items
        )

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
            result["default_page_id"] = default_page_id
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
        if "default_page_id" in project_properties:
            repo_settings["default_page_id"] = project_properties["default_page_id"]
        save_repo_settings(self.repo_root, repo_settings)

    def get_pending_delta(self, timeout_ms: int = 0) -> dict[str, Any] | None:
        return self.fs_sync_service.get_pending_delta(timeout_ms)

    @property
    def blob_storage_adapter(self):
        if self._blob_storage_adapter is None:

            self._blob_storage_adapter = FileStorageAdapter(
                self.repo_root,
                project_manager=self,
            )
        return self._blob_storage_adapter
