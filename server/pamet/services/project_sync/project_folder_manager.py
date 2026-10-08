from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from sivkit.libs.model import Entity, dump_to_dict
from sivkit.storage.change import Change
from sivkit.storage.delta import Delta

from pamet.desktop_app.config import (
    create_repo_settings,
    get_repo_settings,
    repo_settings_path,
)
from pamet.model.arrow import Arrow
from pamet.model.page import Page
from pamet.services.backup import BackupService
from pamet.services.file_system_watcher import FileSystemWatcher
from pamet.storage.canvas_html import write_canvas_file
from pamet.storage.file_storage_adapter import FileStorageAdapter, rebuild_file_index
from pamet.storage.migrations.manager import MigrationManager
from pamet.storage.pamet_in_memory_store import PametInMemoryStore
from pamet.storage.project_walk import iter_canvas_paths, walk_project
from pamet.storage.service_utils import (
    CanvasParseError,
    ForeignCanvasFile,
    read_canvas_file,
)

log = logging.getLogger(__name__)


@dataclass
class ProjectSnapshot:
    """What a project scan read from disk. Not tied to any store or thread."""

    entities: list[Entity] = field(default_factory=list)
    exclude_patterns: list[str] = field(default_factory=list)
    failed_canvas_paths: set[str] = field(default_factory=set)


def scan_project(project_id: str, repo_root: Path) -> ProjectSnapshot:
    """Blocking: migrate, read all .canvas files, rebuild the file index.

    Runs in a worker thread.
    """
    MigrationManager(repo_root).do_all_migrations()

    if not repo_settings_path(repo_root).exists():
        create_repo_settings(repo_root, repo_id=project_id, title=repo_root.name)

    settings = get_repo_settings(repo_root)
    snapshot = ProjectSnapshot(
        exclude_patterns=[
            pat for pat, enabled in settings.get("files.exclude", {}).items() if enabled
        ]
    )

    for canvas_path in iter_canvas_paths(repo_root, snapshot.exclude_patterns):
        try:
            entities = read_canvas_file(canvas_path, repo_root)
        except ForeignCanvasFile:
            continue
        except CanvasParseError:
            log.warning("Failed to parse canvas file: %s", canvas_path)
            snapshot.failed_canvas_paths.add(str(canvas_path))
            continue
        snapshot.entities.extend(entities.values())

    rebuild_file_index(repo_root, snapshot.entities)
    return snapshot


class ProjectFolderManager:
    """
    Per-project desktop runtime owner.

    Owns an in-memory entity store (PametInMemoryStore) and all filesystem
    I/O for .canvas files.  File blob storage is delegated to
    ``FileStorageAdapter`` (``self.file_storage``).  The
    ``FileSystemWatcher`` handles change detection.
    """

    def __init__(self, project_id: str, repo_root: Path, snapshot: ProjectSnapshot):
        self.project_id = project_id
        self.repo_root = Path(repo_root)
        self.store = PametInMemoryStore()
        self.write_lock = threading.Lock()  # Held during writes to suppress watcher
        self.failed_watch_count: int = 0
        self.failed_canvas_paths = set(snapshot.failed_canvas_paths)
        self._exclude_patterns = list(snapshot.exclude_patterns)
        for entity in snapshot.entities:
            self.store.insert_one(entity)

        # Not started: the watchdog watcher replaces it (M4).
        self.fs_watcher = FileSystemWatcher(self)
        self.file_storage = FileStorageAdapter(self.repo_root, self.store)

        # Backup service — always present (for querying), scheduling
        # controlled by backups_enabled property
        self.backup_service = BackupService(
            backup_folder=self.repo_root / ".pamet" / "backups",
            store=self.store,
        )

    # -- Lifecycle -------------------------------------------------------------

    async def unload(self) -> None:
        await self.backup_service.close()
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
        """Recursively yield all non-ignored paths under *root*."""
        return walk_project(self.repo_root, self._exclude_patterns, root, budget=budget)

    # -- Canvas file I/O -------------------------------------------------------

    def _iter_canvas_page_paths(self) -> Iterator[Path]:
        return iter_canvas_paths(self.repo_root, self._exclude_patterns)

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
    ) -> Path:
        """Assemble and write a .canvas file for the given page.

        *page_path* is the project-relative path (e.g. ``notes/my-page.canvas``).
        The ``path`` key is stripped from the serialized data (inferred on read).
        """
        file_data = dict(page_dict)
        file_data.pop("path", None)
        file_data["notes"] = notes
        file_data["arrows"] = arrows
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

        for child in self.store.find(parent_id=page_id):
            child_dict = dump_to_dict(child)
            if isinstance(child, Arrow):
                arrows.append(child_dict)
            else:
                notes.append(child_dict)

        self.write_page_canvas_file(page_path, page_dict, notes, arrows)
