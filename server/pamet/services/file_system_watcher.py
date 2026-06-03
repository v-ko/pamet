from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import TYPE_CHECKING, Any, Set, cast

from PySide6.QtCore import QFileSystemWatcher, QTimer
from sivkit.logging import get_logger
from sivkit.storage.change import Change
from sivkit.storage.delta import Delta

from pamet.model.page import Page
from pamet.services.constants import CANVAS_FILE_EXT
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


class FileSystemWatcher:
    """
    Filesystem change-detection service.

    Watches the project folder via QFileSystemWatcher, debounces events, diffs
    changed .canvas files against the PFM entity store using delta arithmetic,
    and pushes deltas to subscribers.

    All file I/O (reading/writing .canvas files, migrations, media) lives in
    ProjectFolderManager — this service is purely reactive.
    """

    def __init__(self, project_folder_manager: "ProjectFolderManager"):
        self.project_folder_manager = project_folder_manager
        self._watcher: QFileSystemWatcher | None = None
        self._pending_delta = Delta()

        # Single subscriber queue (fed from Qt thread via call_soon_threadsafe)
        self._queue: asyncio.Queue | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

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

    async def deltas_stream(self) -> AsyncGenerator[dict[str, Any]]:
        """Async generator yielding delta dicts as filesystem changes are detected.

        Only one subscriber at a time is supported.
        Flushes any accumulated pending delta first, then streams new
        deltas as they are detected by the filesystem watcher.
        """
        if self._queue is not None:
            raise RuntimeError("Already subscribed — only one subscriber supported")

        self._loop = asyncio.get_running_loop()
        self._queue = asyncio.Queue()
        try:
            # Flush any accumulated pending delta
            if not self._pending_delta.is_empty():
                delta_dict = self._pending_delta.asdict()
                self._pending_delta = Delta()
                yield delta_dict

            while True:
                delta_dict = await self._queue.get()
                yield delta_dict
        finally:
            self._queue = None
            self._loop = None

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
                "[FileSystemWatcher] Failed to watch %d/%d new dirs "
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
                    "[FileSystemWatcher] Failed to watch %d/%d dirs "
                    "on startup (possible inotify limit).",
                    len(failed),
                    len(dirs),
                )
        self._watcher.directoryChanged.connect(self._on_directory_changed)  # type: ignore
        self._watcher.fileChanged.connect(self._on_file_changed)  # type: ignore
        log.info(
            "[FileSystemWatcher] Watching %s directories under %s"
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
                "[FileSystemWatcher] Processing %d directory changes",
                len(dir_changes),
            )
            self._scan_changed_directories(dir_changes)

        for path in file_changes:
            log.info("[FileSystemWatcher] Processing file change: %s", path)
            self._diff_canvas_file(Path(path))

        if not self._pending_delta.is_empty():
            if self._queue is not None and self._loop is not None:
                delta_dict = self._pending_delta.asdict()
                self._pending_delta = Delta()
                self._loop.call_soon_threadsafe(self._queue.put_nowait, delta_dict)

    def _diff_canvas_file(self, canvas_path: Path) -> None:
        """Read a changed .canvas file and diff against the store using delta arithmetic.

        Builds CREATE-snapshot deltas for both disk and mem, then:
            diff = mem_snapshot.reversed().merge_with_priority(disk_snapshot)
        Applies the resulting diff to the store and accumulates it for polling.
        """
        store = self.project_folder_manager.store

        if not canvas_path.exists():
            # File deleted — handled by _scan_changed_directories
            return

        try:
            disk_entities = read_canvas_file(canvas_path, self.repo_root)
        except ForeignCanvasFile:
            return
        except CanvasParseError:
            log.warning("Failed to parse canvas file: %s", canvas_path)
            self.project_folder_manager.failed_canvas_paths.add(str(canvas_path))
            return
        self.project_folder_manager.failed_canvas_paths.discard(str(canvas_path))

        # Extract page_id from the parsed entities (filename is no longer the id)
        page_id = None
        for entity in disk_entities.values():
            if isinstance(entity, Page):
                page_id = entity.id
                break
        if page_id is None:
            log.warning("No Page entity found in canvas file: %s", canvas_path)
            return

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

    def _scan_changed_directories(self, changed_dirs: set[str]) -> None:
        """Scoped scan of changed directories for new/deleted/moved canvas files.

        For each changed directory: list .canvas files, parse to get page ids,
        compare against store pages in those folders.  Cross-directory moves
        are correlated across the debounced batch of changed dirs.
        """
        store = self.project_folder_manager.store
        repo_root = self.repo_root

        # 1. Scan changed dirs for .canvas files and parse page ids
        disk_pages: dict[str, Path] = {}  # {page_id: canvas_path}
        changed_folders: set[str] = set()
        for dir_str in changed_dirs:
            dir_path = Path(dir_str)
            if not dir_path.is_dir():
                continue
            rel_folder = dir_path.relative_to(repo_root).as_posix()
            if rel_folder == ".":
                rel_folder = ""
            changed_folders.add(rel_folder)
            try:
                entries = sorted(dir_path.iterdir(), key=lambda p: p.name)
            except OSError:
                continue
            for entry in entries:
                if entry.is_file() and entry.name.endswith(CANVAS_FILE_EXT):
                    try:
                        entities = read_canvas_file(entry, repo_root)
                    except (ForeignCanvasFile, CanvasParseError):
                        continue
                    for entity in entities.values():
                        if isinstance(entity, Page):
                            disk_pages[entity.id] = entry
                            break

        # 2. Get store pages whose folder matches any changed directory
        store_pages_in_dirs: dict[str, Page] = {}
        for page_entity in cast(list[Page], list(store.find(type=Page))):
            if page_entity.folder in changed_folders:
                store_pages_in_dirs[page_entity.id] = page_entity

        # 3. New or moved pages (on disk but not in store for these dirs)
        for page_id, canvas_path in disk_pages.items():
            if page_id not in store_pages_in_dirs:
                # Could be new, or moved from a different dir
                existing = store.find_one(id=page_id)
                if existing is not None:
                    # Moved from another folder — diff will update the path
                    pass
                self._diff_canvas_file(canvas_path)
            else:
                # Check if path changed (rename within same dir)
                new_path = canvas_path.relative_to(repo_root).as_posix()
                if store_pages_in_dirs[page_id].path != new_path:
                    self._diff_canvas_file(canvas_path)

        # 4. Deleted pages (in store for these dirs but not on disk)
        for page_id, page_entity in store_pages_in_dirs.items():
            if page_id in disk_pages:
                continue

            # Page is gone from its known folder — remove it
            for child in store.find(parent_id=page_id):
                self._pending_delta.add_change(store.remove_one(child))
            self._pending_delta.add_change(store.remove_one(page_entity))
