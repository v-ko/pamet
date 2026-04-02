from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable, Set

from fusion.logging import get_logger
from PySide6.QtCore import QFileSystemWatcher, QTimer

from pamet.storage.migrations.manager import MigrationManager
from pamet.storage.migrations.v4_to_v5 import CANVAS_FILE_EXT

log = get_logger(__name__)

# Debounce tolerance for filesystem events (milliseconds).
# Rapid create/delete/rename sequences (e.g. editor save via tmp file)
# are coalesced into a single processing pass.
FS_EVENT_DEBOUNCE_MS = 100

if TYPE_CHECKING:
    from pamet.services.project_sync.project_folder_manager import ProjectFolderManager


_IGNORED_DIRS = {
    ".pamet",
    "__migration_backup_v2_to_v3__",
    "__migration_backup_v3_to_v4__",
    "__migration_backup_v4_to_v5__",
}


class CanvasParseError(Exception):
    """Raised when a .canvas file cannot be parsed."""


_FILE_ITEM_TYPE_NAMES = {"FileItem", "ImageItem"}


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
        self._pending_delta: dict[str, Any] = {}
        self._pending_delta_event = threading.Event()
        self._write_lock = threading.Lock()  # Held during writes to suppress watcher

        # Debounce: accumulate changed paths, process after timer fires
        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(FS_EVENT_DEBOUNCE_MS)
        self._debounce_timer.timeout.connect(self._process_debounced_events)
        self._pending_dir_changes: set[str] = set()
        self._pending_file_changes: set[str] = set()

    @property
    def repo_root(self) -> Path:
        return self.project_folder_manager.repo_root

    def _iter_canvas_page_paths(self) -> Iterable[Path]:
        for dirpath, dirnames, filenames in os.walk(self.repo_root):
            dirnames[:] = [
                dirname for dirname in dirnames if dirname not in _IGNORED_DIRS
            ]
            for fname in filenames:
                if fname.endswith(CANVAS_FILE_EXT):
                    yield Path(dirpath) / fname

    def read_all_entities(self) -> dict[str, dict[str, Any]]:
        """Read all .canvas files and return a flat entity_id → entity_dict map."""
        entities: dict[str, dict[str, Any]] = {}
        for canvas_path in self._iter_canvas_page_paths():
            try:
                with open(canvas_path, encoding="utf-8") as f:
                    page_data = json.load(f)
            except Exception as exc:
                raise CanvasParseError(
                    f"Failed to read canvas file {canvas_path}"
                ) from exc

            page_id = page_data.get("id")
            if not page_id:
                raise CanvasParseError(f"Canvas file {canvas_path} has no 'id' field")

            # Extract child arrays before storing the page entity
            notes = page_data.pop("notes", [])
            arrows = page_data.pop("arrows", [])
            file_items = page_data.pop("file_items", [])

            entities[page_id] = page_data

            for note in notes:
                note_id = note.get("id")
                if note_id:
                    entities[note_id] = note
            for arrow in arrows:
                arrow_id = arrow.get("id")
                if arrow_id:
                    entities[arrow_id] = arrow
            for file_item in file_items:
                fi_id = file_item.get("id")
                if fi_id:
                    entities[fi_id] = file_item

        log.info("Read %d entities from %s", len(entities), self.repo_root)
        return entities

    def compute_bootstrap_delta(self) -> dict[str, Any]:
        """Return the full filesystem state as a DeltaData of CREATE entries."""
        entities = self.read_all_entities()
        delta: dict[str, Any] = {}
        for entity_id, entity_dict in entities.items():
            # CREATE change: [entity_id, {}, full_entity_state]
            delta[entity_id] = [entity_id, {}, entity_dict]
        return delta

    def write_page_canvas_file(
        self,
        page_id: str,
        page_dict: dict[str, Any],
        notes: list[dict[str, Any]],
        arrows: list[dict[str, Any]],
        file_items: list[dict[str, Any]] | None = None,
    ) -> Path:
        """Assemble and write a .canvas file for the given page."""
        file_data = dict(page_dict)
        file_data["notes"] = notes
        file_data["arrows"] = arrows
        if file_items:
            file_data["file_items"] = file_items
        canvas_path = self.repo_root / f"{page_id}{CANVAS_FILE_EXT}"
        with self._write_lock:
            with open(canvas_path, "w", encoding="utf-8") as f:
                json.dump(file_data, f, ensure_ascii=False, indent=4)
        return canvas_path

    def delete_page_canvas_file(self, page_id: str) -> None:
        """Delete the .canvas file for the given page, if it exists."""
        canvas_path = self.repo_root / f"{page_id}{CANVAS_FILE_EXT}"
        with self._write_lock:
            if canvas_path.exists():
                canvas_path.unlink()

    def get_pending_delta(self, timeout_ms: int = 0) -> dict[str, Any] | None:
        """Return accumulated FS-change delta and clear it.

        If *timeout_ms* > 0 and no delta is available yet, block up to that
        long waiting for filesystem changes before returning.
        """
        if not self._pending_delta and timeout_ms > 0:
            self._pending_delta_event.wait(timeout=timeout_ms / 1000)
        if not self._pending_delta:
            return None
        delta = self._pending_delta
        self._pending_delta = {}
        self._pending_delta_event.clear()
        return delta

    def _collect_dirs_recursive(self) -> list[str]:
        paths: list[str] = [str(self.repo_root)]
        for dirpath, dirnames, _filenames in os.walk(self.repo_root):
            dirnames[:] = [
                dirname for dirname in dirnames if dirname not in _IGNORED_DIRS
            ]
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
        self._ensure_subdirs_watched()
        if self._write_lock.locked():
            return
        self._pending_dir_changes.add(path)
        self._debounce_timer.start()

    def _on_file_changed(self, path: str) -> None:
        if self._write_lock.locked():
            return
        if not path.endswith(CANVAS_FILE_EXT):
            return
        self._pending_file_changes.add(path)
        self._debounce_timer.start()

    def _process_debounced_events(self) -> None:
        dir_changes = self._pending_dir_changes
        file_changes = self._pending_file_changes
        self._pending_dir_changes = set()
        self._pending_file_changes = set()

        if dir_changes:
            log.info(
                "[FileSystemSyncService] Processing %d directory changes",
                len(dir_changes),
            )
            self._scan_for_new_and_deleted_pages()

        for path in file_changes:
            log.info("[FileSystemSyncService] Processing file change: %s", path)
            self._diff_canvas_file(Path(path))

        if self._pending_delta:
            self._pending_delta_event.set()

    def _diff_canvas_file(self, canvas_path: Path) -> None:
        """Read a changed .canvas file and diff against the in-memory entity store."""
        entity_store = self.project_folder_manager._entity_store

        if not canvas_path.exists():
            # File deleted — handled by _scan_for_new_and_deleted_pages
            return

        try:
            with open(canvas_path, encoding="utf-8") as f:
                page_data = json.load(f)
        except Exception as exc:
            raise CanvasParseError(
                f"Failed to read changed canvas file {canvas_path}"
            ) from exc

        page_id = page_data.get("id")
        if not page_id:
            raise CanvasParseError(
                f"Changed canvas file {canvas_path} has no 'id' field"
            )
            return

        notes = page_data.pop("notes", [])
        arrows = page_data.pop("arrows", [])
        file_items = page_data.pop("file_items", [])

        # Build new entity set from the file
        new_entities: dict[str, dict[str, Any]] = {page_id: page_data}
        for note in notes:
            nid = note.get("id")
            if nid:
                new_entities[nid] = note
        for arrow in arrows:
            aid = arrow.get("id")
            if aid:
                new_entities[aid] = arrow
        for fi in file_items:
            fi_id = fi.get("id")
            if fi_id:
                new_entities[fi_id] = fi

        # Collect all current entity ids belonging to this page
        old_page_entity_ids: set[str] = set()
        if page_id in entity_store:
            old_page_entity_ids.add(page_id)
        for eid, entity in entity_store.items():
            if entity.get("parent_id") == page_id:
                old_page_entity_ids.add(eid)

        new_ids = set(new_entities.keys())

        # Created entities
        for eid in new_ids - old_page_entity_ids:
            self._pending_delta[eid] = [eid, {}, new_entities[eid]]
            entity_store[eid] = new_entities[eid]

        # Deleted entities
        for eid in old_page_entity_ids - new_ids:
            old_entity = entity_store.pop(eid, {})
            self._pending_delta[eid] = [eid, old_entity, {}]

        # Updated entities
        for eid in new_ids & old_page_entity_ids:
            old_entity = entity_store.get(eid, {})
            new_entity = new_entities[eid]
            if old_entity != new_entity:
                # Compute forward/reverse components (only changed fields)
                forward: dict[str, Any] = {}
                reverse: dict[str, Any] = {}
                all_keys = set(old_entity.keys()) | set(new_entity.keys())
                for key in all_keys:
                    old_val = old_entity.get(key)
                    new_val = new_entity.get(key)
                    if old_val != new_val:
                        forward[key] = new_val
                        reverse[key] = old_val
                if forward:
                    self._pending_delta[eid] = [eid, reverse, forward]
                    entity_store[eid] = new_entity

    def _scan_for_new_and_deleted_pages(self) -> None:
        """Detect new or deleted .canvas files by comparing filesystem with entity store."""
        entity_store = self.project_folder_manager._entity_store

        # Collect page ids currently on disk
        disk_page_ids: set[str] = set()
        canvas_paths: dict[str, Path] = {}
        for canvas_path in self._iter_canvas_page_paths():
            # Extract page id from filename: {page_id}.canvas
            page_id = canvas_path.stem
            disk_page_ids.add(page_id)
            canvas_paths[page_id] = canvas_path

        # Collect page ids in entity store
        store_page_ids: set[str] = {
            eid
            for eid, entity in entity_store.items()
            if entity.get("type_name") == "Page"
        }

        # New pages on disk
        for page_id in disk_page_ids - store_page_ids:
            self._diff_canvas_file(canvas_paths[page_id])

        # Deleted pages (on disk but no longer present)
        for page_id in store_page_ids - disk_page_ids:
            # Remove page and all its children
            children_to_remove = [
                eid
                for eid, entity in entity_store.items()
                if entity.get("parent_id") == page_id
            ]
            for eid in children_to_remove:
                old_entity = entity_store.pop(eid, {})
                self._pending_delta[eid] = [eid, old_entity, {}]
            old_page = entity_store.pop(page_id, {})
            self._pending_delta[page_id] = [page_id, old_page, {}]

    def index_folder(self) -> int:
        count = 0
        for _ in self._iter_canvas_page_paths():
            count += 1
        log.info("Indexed %s canvas page file(s) in %s", count, self.repo_root)
        return count
