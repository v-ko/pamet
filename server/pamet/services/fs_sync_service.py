from __future__ import annotations

import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any, Set

from fusion.libs.entity.change import Change
from fusion.libs.entity.delta import Delta
from fusion.logging import get_logger
from PySide6.QtCore import QFileSystemWatcher, QTimer

from pamet.model.page import Page
from pamet.storage.migrations.v4_to_v5 import CANVAS_FILE_EXT
from pamet.storage.service_utils import (
    CanvasParseError,
    ForeignCanvasFile,
    read_canvas_file,
)

log = get_logger(__name__)

# Debounce tolerance for filesystem events (milliseconds).
# Rapid create/delete/rename sequences (e.g. editor save via tmp file)
# are coalesced into a single processing pass.
FS_EVENT_DEBOUNCE_MS = 100

if TYPE_CHECKING:
    from pamet.services.project_sync.project_folder_manager import ProjectFolderManager


class FileSystemSyncService:
    """
    Filesystem change-detection service.

    Watches the project folder via QFileSystemWatcher, debounces events, diffs
    changed .canvas files against the PFM entity store using delta arithmetic,
    and accumulates deltas for the web app to poll.

    All file I/O (reading/writing .canvas files, migrations, media) lives in
    ProjectFolderManager — this service is purely reactive.
    """

    def __init__(self, project_folder_manager: "ProjectFolderManager"):
        self.project_folder_manager = project_folder_manager
        self._watcher: QFileSystemWatcher | None = None
        self._pending_delta = Delta()
        self._pending_delta_event = threading.Event()
        self._delta_consumer_lock = threading.Lock()

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

    def get_pending_delta(self, timeout_ms: int = 0) -> dict[str, Any] | None:
        """Return accumulated FS-change delta as wire-format dict and clear it.

        If *timeout_ms* > 0 and no delta is available yet, block up to that
        long waiting for filesystem changes before returning.

        Only one consumer may poll at a time.
        """
        if not self._delta_consumer_lock.acquire(blocking=False):
            raise RuntimeError("Another consumer is already polling for deltas")
        try:
            if self._pending_delta.is_empty() and timeout_ms > 0:
                self._pending_delta_event.wait(timeout=timeout_ms / 1000)
            if self._pending_delta.is_empty():
                return None
            delta = self._pending_delta
            self._pending_delta = Delta()
            self._pending_delta_event.clear()
            return delta.asdict()
        finally:
            self._delta_consumer_lock.release()

    def _watch_new_subdirs(self, changed_dir: str) -> None:
        """Add watches for new subdirectories under *changed_dir*.

        Scoped walk: only the subtree rooted at the changed directory is
        visited, keeping cost proportional to the change.
        """
        if self._watcher is None:
            return
        pfm = self.project_folder_manager
        changed_path = Path(changed_dir)
        if not changed_path.is_dir():
            return
        watched: Set[str] = set(self._watcher.directories())
        new_dirs = [
            str(p)
            for p in pfm._walk_project(changed_path)
            if p.is_dir() and str(p) not in watched
        ]
        if not new_dirs:
            return
        failed = self._watcher.addPaths(new_dirs)
        if failed:
            pfm.failed_watch_count += len(failed)
            log.warning(
                "[FileSystemSyncService] Failed to watch %d/%d new dirs "
                "(total failures: %d). Possible inotify limit reached.",
                len(failed),
                len(new_dirs),
                pfm.failed_watch_count,
            )

    def start_watching(self) -> None:
        if self._watcher is not None:
            return
        self._watcher = QFileSystemWatcher()
        pfm = self.project_folder_manager
        dirs = [str(self.repo_root)] + [
            str(p) for p in pfm._walk_project() if p.is_dir()
        ]
        if dirs:
            failed = self._watcher.addPaths(dirs)
            if failed:
                self.project_folder_manager.failed_watch_count += len(failed)
                log.warning(
                    "[FileSystemSyncService] Failed to watch %d/%d dirs "
                    "on startup (possible inotify limit).",
                    len(failed),
                    len(dirs),
                )
        self._watcher.directoryChanged.connect(self._on_directory_changed)  # type: ignore
        self._watcher.fileChanged.connect(self._on_file_changed)  # type: ignore
        log.info(
            "[FileSystemSyncService] Watching %s directories under %s"
            " (failed watches: %d)",
            len(self._watcher.directories()),
            self.repo_root,
            self.project_folder_manager.failed_watch_count,
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
        self._watch_new_subdirs(path)
        self._pending_dir_changes.add(path)
        self._debounce_timer.start()

    def _on_file_changed(self, path: str) -> None:
        if not path.endswith(CANVAS_FILE_EXT):
            return
        self._pending_file_changes.add(path)
        self._debounce_timer.start()

    def _process_debounced_events(self) -> None:
        # Skip if we triggered the changes ourselves
        if self.project_folder_manager.write_lock.locked():
            self._pending_dir_changes.clear()
            self._pending_file_changes.clear()
            return

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

        if not self._pending_delta.is_empty():
            self._pending_delta_event.set()

    def _diff_canvas_file(self, canvas_path: Path) -> None:
        """Read a changed .canvas file and diff against the store using delta arithmetic.

        Builds CREATE-snapshot deltas for both disk and mem, then:
            diff = mem_snapshot.reversed().merge_with_priority(disk_snapshot)
        Applies the resulting diff to the store and accumulates it for polling.
        """
        store = self.project_folder_manager.store

        if not canvas_path.exists():
            # File deleted — handled by _scan_for_new_and_deleted_pages
            return

        try:
            disk_entities = read_canvas_file(canvas_path)
        except ForeignCanvasFile:
            return
        except CanvasParseError:
            log.warning("Failed to parse canvas file: %s", canvas_path)
            self.project_folder_manager.failed_canvas_paths.add(str(canvas_path))
            return
        self.project_folder_manager.failed_canvas_paths.discard(str(canvas_path))

        page_id = canvas_path.stem

        # Build disk snapshot delta (all CREATEs)
        disk_delta = Delta.from_changes(
            [Change.create(entity) for entity in disk_entities.values()]
        )

        # Build mem snapshot delta for this page's entities (all CREATEs)
        mem_entities = list(store.find(parent_id=page_id))
        page_entity = store.find_one(id=page_id)
        if page_entity is not None:
            mem_entities.append(page_entity)
        mem_delta = Delta.from_changes(
            [Change.create(entity) for entity in mem_entities]
        )

        # Diff via delta arithmetic: reverse mem + merge disk
        diff = mem_delta.reversed()
        diff.merge_with_priority(disk_delta)

        if diff.is_empty():
            return

        # Apply diff to the store
        applied = store.apply_delta(diff)

        # Accumulate for web app polling
        self._pending_delta.merge_with_priority(applied)

    def _scan_for_new_and_deleted_pages(self) -> None:
        """Full-project scan for new/deleted canvas files.

        Directory events are rare and debounced, so a full walk is acceptable.
        This correctly handles renames, moves, and nested dir creation.
        """
        store = self.project_folder_manager.store

        disk_page_ids: set[str] = set()
        canvas_paths: dict[str, Path] = {}
        for canvas_path in self.project_folder_manager._iter_canvas_page_paths():
            page_id = canvas_path.stem
            disk_page_ids.add(page_id)
            canvas_paths[page_id] = canvas_path

        store_page_ids: set[str] = {entity.id for entity in store.find(type=Page)}

        for page_id in disk_page_ids - store_page_ids:
            self._diff_canvas_file(canvas_paths[page_id])

        for page_id in store_page_ids - disk_page_ids:
            for child in store.find(parent_id=page_id):
                self._pending_delta.add_change(store.remove_one(child))
            page_entity = store.find_one(id=page_id)
            if page_entity is not None:
                self._pending_delta.add_change(store.remove_one(page_entity))
