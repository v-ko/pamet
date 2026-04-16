from __future__ import annotations

import threading
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Iterator

from fusion.libs.entity import dump_to_dict
from fusion.libs.entity.change import Change
from fusion.libs.entity.delta import Delta
from fusion.logging import get_logger

from pamet.desktop_app.config import get_repo_settings
from pamet.model.arrow import Arrow
from pamet.model.file_item import FileItem
from pamet.model.page import Page
from pamet.services.backup import BackupService
from pamet.services.constants import MAX_WALK_ENTRIES
from pamet.services.file_system_watcher import FileSystemWatcher
from pamet.storage.canvas_html import write_canvas_file
from pamet.storage.file_storage_adapter import FileStorageAdapter
from pamet.storage.migrations.manager import (
    MIGRATION_BACKUP_DIR_NAMES,
    MigrationManager,
)
from pamet.storage.migrations.v4_to_v5 import CANVAS_FILE_EXT
from pamet.storage.pamet_in_memory_store import PametInMemoryStore
from pamet.storage.service_utils import (
    CanvasParseError,
    ForeignCanvasFile,
    ProjectTooLargeError,
    read_canvas_file,
)

log = get_logger(__name__)

_IGNORED_DIRS = {".pamet"} | MIGRATION_BACKUP_DIR_NAMES


def _matches_exclude(name: str, rel_path: str, patterns: list[str]) -> bool:
    """Match a file/dir name against exclude patterns.

    Supports:
      - bare names/globs: matched against the basename (e.g. "build", "*.tmp")
      - **/name patterns: matched against the basename (any depth)
      - path patterns (contain /): matched against the relative path from repo root
    """
    for pat in patterns:
        if pat.startswith("**/"):
            # "**/<glob>" → match basename at any depth
            if fnmatch(name, pat[3:]):
                return True
        elif "/" in pat:
            # path-relative pattern → match against relative path
            if fnmatch(rel_path, pat):
                return True
        else:
            # bare name/glob → match against basename
            if fnmatch(name, pat):
                return True
    return False


class ProjectFolderManager:
    """
    Per-project desktop runtime owner.

    Owns an in-memory entity store (PametInMemoryStore) and all filesystem
    I/O for .canvas files.  File blob storage is delegated to
    ``FileStorageAdapter`` (``self.file_storage``).  The
    ``FileSystemWatcher`` handles change detection.
    """

    def __init__(self, project_id: str, repo_root: Path):
        self.project_id = project_id
        self.repo_root = Path(repo_root)
        self.store = PametInMemoryStore()
        self.write_lock = threading.Lock()  # Held during writes to suppress watcher
        self.failed_watch_count: int = 0
        self.failed_canvas_paths: set[str] = set()  # Paths that failed to parse
        self.migration_manager = MigrationManager(self.repo_root)

        # Load user-configured exclude patterns from repo settings
        settings = get_repo_settings(self.repo_root)
        self._exclude_patterns: list[str] = [
            pat for pat, enabled in settings.get("files.exclude", {}).items() if enabled
        ]

        self.fs_watcher = FileSystemWatcher(self)
        self.file_storage = FileStorageAdapter(self.repo_root, self.store)

        # Backup service — always present (for querying), scheduling
        # controlled by backups_enabled property
        self.backup_service = BackupService(
            backup_folder=self.repo_root / ".pamet" / "backups",
            store=self.store,
        )

    # -- Lifecycle -------------------------------------------------------------

    def load(self) -> None:
        self.migration_manager.do_all_migrations()
        file_items = self._load_all_entities()
        self.file_storage.rebuild_index(file_items)
        log.info(
            "Loaded project %s from %s",
            self.project_id,
            self.repo_root,
        )
        self.fs_watcher.start_watching()

    def _load_all_entities(self) -> list[FileItem]:
        """Read all .canvas files and populate the store.

        Returns the loaded ``FileItem`` (and subclass) entities so the
        caller can pass them to the file-storage index without a second
        store scan.
        """
        file_items: list[FileItem] = []
        for canvas_path in self._iter_canvas_page_paths():
            try:
                entities = read_canvas_file(canvas_path, self.repo_root)
            except ForeignCanvasFile:
                continue
            except CanvasParseError:
                log.warning("Failed to parse canvas file: %s", canvas_path)
                self.failed_canvas_paths.add(str(canvas_path))
                continue
            self.failed_canvas_paths.discard(str(canvas_path))
            for entity in entities.values():
                self.store.insert_one(entity)
                if isinstance(entity, FileItem):
                    file_items.append(entity)
        return file_items

    def unload(self) -> None:
        self.backup_service.stop()
        self.fs_watcher.stop_watching()
        self.file_storage.close()
        self.store.clear()

    # -- Project tree walking ---------------------------------------------------

    def _walk_project(
        self,
        root: Path | None = None,
        *,
        budget: list[int] | None = None,
    ) -> Iterator[Path]:
        """Recursively yield all non-ignored paths under *root*.

        Yields both directories and files.  Directories are yielded before
        their contents (pre-order).  Uses ``os.scandir`` for a single clear
        recursion with consistent ignore/exclude handling everywhere.

        *budget* is a one-element list used as a mutable counter.  When the
        counter reaches zero, ``ProjectTooLargeError`` is raised.
        """
        if root is None:
            root = self.repo_root
        if budget is None:
            budget = [MAX_WALK_ENTRIES]

        try:
            entries = sorted(root.iterdir(), key=lambda p: p.name)
        except OSError:
            return

        for entry in entries:
            budget[0] -= 1
            if budget[0] <= 0:
                raise ProjectTooLargeError(
                    f"Project folder {self.repo_root} exceeds the walk "
                    f"budget of {MAX_WALK_ENTRIES} filesystem entries"
                )

            if entry.is_symlink():
                continue

            rel = entry.relative_to(self.repo_root).as_posix()

            if entry.is_dir():
                if entry.name in _IGNORED_DIRS:
                    continue
                if _matches_exclude(entry.name, rel, self._exclude_patterns):
                    continue
                yield entry
                yield from self._walk_project(entry, budget=budget)
            else:
                if _matches_exclude(entry.name, rel, self._exclude_patterns):
                    continue
                yield entry

    # -- Canvas file I/O -------------------------------------------------------

    def _iter_canvas_page_paths(self) -> Iterator[Path]:
        for path in self._walk_project():
            if not path.is_dir() and path.suffix == CANVAS_FILE_EXT:
                yield path

    def compute_bootstrap_delta(self) -> dict[str, Any]:
        """Return the full store state as wire-format DeltaData of CREATE entries."""
        delta = Delta.from_changes(
            [Change.create(entity) for entity in self.store.find()]
        )
        return delta.asdict()

    def write_page_canvas_file(
        self,
        page_path: str,
        page_dict: dict[str, Any],
        notes: list[dict[str, Any]],
        arrows: list[dict[str, Any]],
        file_items: list[dict[str, Any]] | None = None,
    ) -> Path:
        """Assemble and write a .canvas file for the given page.

        *page_path* is the project-relative path (e.g. ``notes/my-page.canvas``).
        The ``path`` key is stripped from the serialized data (inferred on read).
        """
        file_data = dict(page_dict)
        file_data.pop("path", None)
        file_data["notes"] = notes
        file_data["arrows"] = arrows
        if file_items:
            file_data["file_items"] = file_items
        canvas_path = self.repo_root / page_path
        with self.write_lock:
            canvas_path.parent.mkdir(parents=True, exist_ok=True)
            write_canvas_file(canvas_path, file_data)
        return canvas_path

    def delete_page_canvas_file(self, page_path: str) -> None:
        """Delete the .canvas file at the given project-relative *page_path*."""
        canvas_path = self.repo_root / page_path
        with self.write_lock:
            if canvas_path.exists():
                canvas_path.unlink()

    # -- Delta application (user edits → filesystem) --------------------------

    def apply_delta(self, delta_data: dict[str, Any]) -> None:
        """Apply a wire-format DeltaData dict to the store and write affected pages."""
        delta = Delta.from_data(delta_data)
        applied = self.store.apply_delta(delta)

        pages_to_write: set[str] = set()
        deleted_page_paths: dict[str, str] = {}
        old_canvas_paths: list[str] = []

        for change in applied.changes():
            if change.is_delete():
                # Entity is gone from the store; use reverse_component
                # (full old state from Change.delete → dump_to_dict).
                rev = change.reverse_component
                if rev.get("type_name") == "Page":
                    deleted_page_paths[change.entity_id] = rev.get("path", "")
                else:
                    parent_id = rev.get("parent_id", "")
                    if parent_id:
                        pages_to_write.add(parent_id)

            elif change.is_create():
                entity = self.store.find_one(id=change.entity_id)
                if entity is None:
                    continue
                if isinstance(entity, Page):
                    pages_to_write.add(entity.id)
                elif entity.parent_id:
                    pages_to_write.add(entity.parent_id)

            elif change.is_update():
                entity = self.store.find_one(id=change.entity_id)
                if entity is None:
                    continue
                if isinstance(entity, Page):
                    pages_to_write.add(entity.id)
                    # Path rename: schedule old canvas file for deletion
                    old_path = change.reverse_component.get("path")
                    if old_path:
                        old_canvas_paths.append(old_path)
                elif entity.parent_id:
                    pages_to_write.add(entity.parent_id)
                    # Reparented child: also rewrite old parent page
                    old_parent_id = change.reverse_component.get("parent_id")
                    if old_parent_id:
                        pages_to_write.add(old_parent_id)

        pages_to_write -= set(deleted_page_paths)

        for page_id in pages_to_write:
            self._write_page_to_disk(page_id)

        for old_path in old_canvas_paths:
            self.delete_page_canvas_file(old_path)

        for path in deleted_page_paths.values():
            if path:
                self.delete_page_canvas_file(path)

        log.info(
            "Applied delta: %d changes, %d pages written, %d deleted",
            sum(1 for _ in applied.changes()),
            len(pages_to_write),
            len(deleted_page_paths),
        )

        # Signal the backup service about written pages
        if pages_to_write:
            self.backup_service.mark_pages_changed(pages_to_write)

    def _write_page_to_disk(self, page_id: str) -> None:
        """Assemble a page's data from the store and write it as a .canvas file."""
        page_entity = self.store.find_one(id=page_id)
        if page_entity is None:
            log.warning("Cannot write page %s: not found in store", page_id)
            return

        page_dict = dump_to_dict(page_entity)
        page_path = page_dict.get("path", "")

        notes: list[dict[str, Any]] = []
        arrows: list[dict[str, Any]] = []
        file_items: list[dict[str, Any]] = []

        for child in self.store.find(parent_id=page_id):
            child_dict = dump_to_dict(child)
            if isinstance(child, Arrow):
                arrows.append(child_dict)
            elif isinstance(child, FileItem):
                file_items.append(child_dict)
            else:
                notes.append(child_dict)

        self.write_page_canvas_file(page_path, page_dict, notes, arrows, file_items)
