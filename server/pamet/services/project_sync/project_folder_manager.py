from __future__ import annotations

import asyncio
import logging
import threading
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from sivkit.libs.model import Entity, dump_to_dict
from sivkit.storage.change import Change
from sivkit.storage.delta import Delta
from sivkit.storage.fs.names import canonical_key

from pamet.desktop_app.config import (
    create_repo_settings,
    get_repo_settings,
    repo_settings_path,
)
from pamet.model.arrow import Arrow
from pamet.model.page import Page
from pamet.services.backup import BackupService
from pamet.services.constants import CANVAS_FILE_EXT
from pamet.services.file_system_watcher import FileSystemWatcher
from pamet.storage.atomic_write import TEMP_SUFFIX
from pamet.storage.canvas_html import dump_canvas_html
from pamet.storage.canvas_writes import (
    PageMove,
    PageWrite,
    SaveRejected,
    check_page_path,
    check_targets,
    write_pages,
)
from pamet.storage.disk_index import DiskEntry, Fingerprint, file_fingerprint
from pamet.storage.file_storage_adapter import FileStorageAdapter, rebuild_file_index
from pamet.storage.migrations.manager import MigrationManager
from pamet.storage.pamet_in_memory_store import PametInMemoryStore
from pamet.storage.project_walk import iter_canvas_paths, walk_project
from pamet.storage.service_utils import (
    CanvasParseError,
    ForeignCanvasFile,
    ProjectProblem,
    read_canvas_file,
)

log = logging.getLogger(__name__)


@dataclass
class ProjectSnapshot:
    """What a project scan read from disk. Not tied to any store or thread."""

    entities: list[Entity] = field(default_factory=list)
    exclude_patterns: list[str] = field(default_factory=list)
    problems: dict[str, ProjectProblem] = field(default_factory=dict)  # by path
    disk_index: dict[str, DiskEntry] = field(default_factory=dict)  # by path


def scan_project(project_id: str, repo_root: Path) -> ProjectSnapshot:
    """Blocking: migrate, read all .canvas files, rebuild the file index.

    Files that claim an id already loaded from a newer file are duplicates
    and aren't loaded. Leftover temp files from interrupted writes are
    deleted. Runs in a worker thread.
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

    def on_list_error(folder: Path, exc: OSError) -> None:
        log.warning("Failed to list folder %s: %s", folder, exc)
        rel = folder.relative_to(repo_root).as_posix()
        snapshot.problems[rel] = ProjectProblem(
            "unlisted_folder", rel, exc.strerror or str(exc)
        )

    parsed: list[tuple[str, Fingerprint | None, dict[str, Entity]]] = []
    for path in walk_project(
        repo_root, snapshot.exclude_patterns, onerror=on_list_error
    ):
        is_temp = path.name.endswith(CANVAS_FILE_EXT + TEMP_SUFFIX)
        if not (is_temp or path.name.endswith(CANVAS_FILE_EXT)) or path.is_dir():
            continue
        if is_temp:
            try:
                path.unlink()
            except OSError as exc:
                log.warning("Failed to delete leftover temp file %s: %s", path, exc)
            continue

        rel = path.relative_to(repo_root).as_posix()
        # Stat first: a change during the read then shows as a new fingerprint
        fingerprint = file_fingerprint(path)
        try:
            entities = read_canvas_file(path, repo_root)
        except ForeignCanvasFile:
            continue
        except CanvasParseError as exc:
            log.warning("Failed to parse canvas file %s: %s", path, exc)
            snapshot.problems[rel] = ProjectProblem("unreadable_file", rel, str(exc))
            snapshot.disk_index[rel] = DiskEntry(fingerprint, read_error=str(exc))
            continue
        parsed.append((rel, fingerprint, entities))

    # The newest file wins duplicate ids; on a tie, path order decides.
    parsed.sort(key=lambda item: (-(item[1][1] if item[1] else 0), item[0]))
    owners: dict[str, str] = {}  # entity id → owning path
    for rel, fingerprint, entities in parsed:
        taken = next((id_ for id_ in entities if id_ in owners), None)
        if taken is None:
            owners.update(dict.fromkeys(entities, rel))
            snapshot.entities.extend(entities.values())
            role = "owner"
        else:
            snapshot.problems[rel] = ProjectProblem(
                "duplicate_id",
                rel,
                f"Id {taken} is already loaded from {owners[taken]}",
            )
            role = "duplicate"
        snapshot.disk_index[rel] = DiskEntry(fingerprint, role, ids=tuple(entities))

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
        self.mutation_lock = asyncio.Lock()  # One save or sweep at a time
        self.failed_watch_count: int = 0
        self.problems = dict(snapshot.problems)
        self.disk_index = dict(snapshot.disk_index)
        self._exclude_patterns = list(snapshot.exclude_patterns)
        for entity in snapshot.entities:
            self.store.insert_one(entity)

        # Not started: the watchdog watcher replaces it (M4).
        self.fs_watcher = FileSystemWatcher(self)

        # Backup service — always present (for querying), scheduling
        # controlled by backups_enabled property
        self.backup_service = BackupService(
            backup_folder=self.repo_root / ".pamet" / "backups",
            store=self.store,
        )
        # Open the index last so failed backup setup cannot leak its engine.
        self.file_storage = FileStorageAdapter(self.repo_root, self.store)

    # -- Lifecycle -------------------------------------------------------------

    async def stop(self) -> None:
        """Stop producers and flush backups while the store is still available."""
        try:
            self.fs_watcher.close_stream()
            self.fs_watcher.stop_watching()
        finally:
            await self.backup_service.close()

    def close(self) -> None:
        """Release storage after DSS has drained the project's history work."""
        try:
            self.file_storage.close()
        finally:
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

    # -- Saving edits (user edits → filesystem) --------------------------------

    async def save(self, delta_data: dict[str, Any]) -> None:
        """Check, apply and write a wire-format delta, one save at a time.

        A rejected delta changes nothing. After a failed write the change
        stays in the store and the error is raised.
        """
        async with self.mutation_lock:
            delta = Delta.from_data(delta_data)
            moves = self._check_page_moves(delta)
            if moves:
                await asyncio.to_thread(check_targets, self.repo_root, moves)
            applied = self.store.apply_delta(delta)
            writes, deletes = self._serialize_changes(applied)
            stats, error = await asyncio.to_thread(
                write_pages, self.repo_root, writes, deletes
            )
            self._update_disk_index(writes, stats)
            if writes:
                self.backup_service.mark_pages_changed({w.ids[0] for w in writes})
            log.info("Saved %d pages, deleted %d", len(writes), len(deletes))
            if error is not None:
                raise error

    def _check_page_moves(self, delta: Delta) -> list[PageMove]:
        """Refuse invalid or colliding page paths before the store changes."""
        moves: list[PageMove] = []
        paths = {page.id: page.path for page in self.store.find(type=Page)}
        for change in delta.changes():
            forward = change.forward_component
            current = self.store.find_one(id=change.entity_id)
            if change.is_delete():
                paths.pop(change.entity_id, None)
            elif change.is_create() and forward.get("type_name") == "Page":
                moves.append(PageMove(change.entity_id, forward.get("path"), None))
            elif isinstance(current, Page) and "path" in forward:
                if forward["path"] != current.path:
                    old_rel = current.path or None
                    moves.append(PageMove(change.entity_id, forward["path"], old_rel))
        for move in moves:
            check_page_path(move.rel, self._exclude_patterns)
            paths[move.page_id] = move.rel
        # As a case-insensitive file system would see them
        counts = Counter(canonical_key(path) for path in paths.values())
        for move in moves:
            if counts[canonical_key(move.rel)] > 1:
                raise SaveRejected(f"Two pages would share the path {move.rel!r}")
        return moves

    def _serialize_changes(self, applied: Delta) -> tuple[list[PageWrite], list[str]]:
        """The pages an applied delta touched, serialized, and deleted pages' files."""
        pages_to_write: set[str] = set()
        deleted_page_paths: dict[str, str] = {}
        old_canvas_paths: dict[str, str] = {}  # page id → path before a rename

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
                    # Path rename: the old file is removed after the write
                    old_path = change.reverse_component.get("path")
                    if old_path and old_path != entity.path:
                        old_canvas_paths[entity.id] = old_path
                elif entity.parent_id:
                    pages_to_write.add(entity.parent_id)
                    # Reparented child: also rewrite old parent page
                    old_parent_id = change.reverse_component.get("parent_id")
                    if old_parent_id:
                        pages_to_write.add(old_parent_id)

        pages_to_write -= set(deleted_page_paths)

        writes = []
        for page_id in pages_to_write:
            write = self._serialize_page(page_id, old_canvas_paths.get(page_id))
            if write is not None:
                writes.append(write)
        return writes, [path for path in deleted_page_paths.values() if path]

    def _serialize_page(self, page_id: str, old_rel: str | None) -> PageWrite | None:
        page_entity = self.store.find_one(id=page_id)
        if page_entity is None:
            log.warning("Cannot write page %s: not found in store", page_id)
            return None

        # The path is inferred on read
        file_data = dump_to_dict(page_entity)
        page_path = file_data.pop("path", "")
        children = list(self.store.find(parent_id=page_id))
        file_data["notes"] = [
            dump_to_dict(c) for c in children if not isinstance(c, Arrow)
        ]
        file_data["arrows"] = [
            dump_to_dict(c) for c in children if isinstance(c, Arrow)
        ]
        data = dump_canvas_html(file_data).encode("utf-8")
        ids = (page_id, *(child.id for child in children))
        return PageWrite(page_path, data, ids, old_rel)

    def _update_disk_index(
        self, writes: list[PageWrite], stats: dict[str, Fingerprint | None]
    ) -> None:
        """Record the files a save touched as they are on disk now."""
        for rel, fingerprint in stats.items():
            if fingerprint is None:
                self.disk_index.pop(rel, None)
                self.problems.pop(rel, None)
        for write in writes:
            fingerprint = stats[write.rel]
            entry = self.disk_index.get(write.rel)
            if fingerprint is None or (entry and entry.fingerprint == fingerprint):
                continue  # Not written
            self.disk_index[write.rel] = DiskEntry(fingerprint, "owner", ids=write.ids)
            self.problems.pop(write.rel, None)
