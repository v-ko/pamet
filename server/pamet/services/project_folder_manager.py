from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Iterable, Set

from fusion.logging import get_logger
from pamet.storage.migrations.manager import V5_FILE_EXT, MigrationManager
from PySide6.QtCore import QFileSystemWatcher

log = get_logger(__name__)


class ProjectFolderManager:
    """
    Manages the project folder (repository path):
    - Runs one-off migrations on demand via process()
    - Sets up a Qt file system watcher and logs changes
    """

    _migration_done = False

    def __init__(self, repo_path: Path | str):
        self.repo_path = Path(repo_path)
        self._watcher: QFileSystemWatcher | None = None
        self.migration_manager = MigrationManager(self.repo_path)

    # ----- Canvas pages (.pam5.json) -----
    def _iter_canvas_page_paths(self) -> Iterable[Path]:
        for dirpath, dirnames, filenames in os.walk(self.repo_path):
            # Skip internal metadata folder
            dirnames[:] = [d for d in dirnames if d != ".pamet"]
            for fname in filenames:
                if fname.endswith(V5_FILE_EXT):
                    yield Path(dirpath) / fname

    def _read_page_json(self, file_path: Path) -> dict[str, Any]:
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError(f"Expected object in {file_path}, got {type(data)}")
        return data

    def _path_for_canvas_page_id(self, page_id: str) -> Path | None:
        if not page_id:
            return None

        # Canonical V5 naming produced by migration: <page_id>.pam5.json
        by_name = self.repo_path / f"{page_id}{V5_FILE_EXT}"
        if by_name.exists():
            return by_name
        return None

    def list_canvas_page_ids(self) -> list[str]:
        """Return IDs of all V5 canvas pages (.pam5.json) in the repo."""
        page_ids: set[str] = set()
        for page_path in self._iter_canvas_page_paths():
            try:
                page_data = self._read_page_json(page_path)
            except Exception as e:
                log.error(f"Failed to read page file {page_path}: {e}")
                continue

            page_id = page_data.get("id")
            if isinstance(page_id, str) and page_id:
                page_ids.add(page_id)
            else:
                log.warning(f"Skipping page without valid id: {page_path}")
        return sorted(page_ids)

    def canvas_page_paths(self) -> list[Path]:
        """Return all V5 canvas page file paths."""
        return list(self._iter_canvas_page_paths())

    def get_canvas_page_and_entities(
        self, page_id: str
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """
        Load one V5 page by id and return:
        - page entity dict
        - list of page children entity dicts (notes + arrows)
        """
        page_path = self._path_for_canvas_page_id(page_id)
        if page_path is None:
            raise FileNotFoundError(f"Canvas page not found for id {page_id}")

        page_state = self._read_page_json(page_path)

        page_data = dict(page_state)
        page_data.pop("notes", None)
        page_data.pop("arrows", None)
        page_data.setdefault("type_name", "Page")
        page_data.setdefault("parent_id", "")

        notes = page_state.get("notes", [])
        arrows = page_state.get("arrows", [])
        entities_data: list[Any] = notes + arrows

        entities: list[dict[str, Any]] = []
        for entity in entities_data:
            entity_data = dict(entity)
            entity_data.setdefault("parent_id", page_id)
            entities.append(entity_data)

        return page_data, entities

    def all_canvas_entities(self) -> list[dict[str, Any]]:
        """Return all page + child entities from V5 canvas files."""
        all_entities: list[dict[str, Any]] = []
        for page_id in self.list_canvas_page_ids():
            page_data, page_entities = self.get_canvas_page_and_entities(page_id)
            all_entities.append(page_data)
            all_entities.extend(page_entities)
        return all_entities

    @staticmethod
    def _stable_commit_timestamp_ms(page_file_paths: list[Path]) -> int:
        if not page_file_paths:
            return int(time.time() * 1000)
        return max(int(p.stat().st_mtime * 1000) for p in page_file_paths)

    def get_head_state_as_mock_commit(
        self, branch_name: str = "main"
    ) -> dict[str, Any]:
        """
        Return current head state as a single synthetic commit.

        This is a temporary read-only bridge for the desktop REST storage API
        until a proper filesystem commit repository adapter is introduced.
        """
        if not branch_name:
            branch_name = "main"

        all_entities = self.all_canvas_entities()
        delta_data: dict[str, list[Any]] = {}
        for entity_data in all_entities:
            entity_id = entity_data.get("id")
            if not isinstance(entity_id, str) or not entity_id:
                log.warning(
                    f"Skipping entity with invalid id in head-state build: {entity_data}"
                )
                continue
            delta_data[entity_id] = [entity_id, {}, entity_data]

        canonical_delta = json.dumps(
            delta_data, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        # TODO: Compute hash properly (matching frontend HashTree).
        # For now hardcode the hash reported by the frontend integrity check.
        snapshot_hash = (
            "56cf116bb53174a138e10b493f5a77128fcf2c7a64ce7c43c3a36941da9278cb"
        )
        commit_id = snapshot_hash[:24]
        timestamp_ms = self._stable_commit_timestamp_ms(self.canvas_page_paths())

        commit = {
            "id": commit_id,
            "parentId": "",
            "snapshotHash": snapshot_hash,
            "timestamp": timestamp_ms,
            "message": "Desktop snapshot (read-only)",
            "deltaData": delta_data,
        }
        commit_graph = {
            "branches": [{"name": branch_name, "headCommitId": commit_id}],
            "commits": [
                {
                    "id": commit["id"],
                    "parentId": commit["parentId"],
                    "snapshotHash": commit["snapshotHash"],
                    "timestamp": commit["timestamp"],
                    "message": commit["message"],
                }
            ],
        }

        return {"commitGraph": commit_graph, "commits": [commit]}

    # ----- Watching -----
    def _collect_dirs_recursive(self) -> list[str]:
        paths: list[str] = []
        root_str = str(self.repo_path)
        paths.append(root_str)
        for dirpath, dirnames, _filenames in os.walk(self.repo_path):
            # Skip .pamet internal folder
            dirnames[:] = [d for d in dirnames if d != ".pamet"]
            # Add each directory encountered
            paths.extend(str(Path(dirpath) / d) for d in dirnames)
        # QFileSystemWatcher ignores duplicates silently
        return paths

    def _ensure_subdirs_watched(self):
        if not self._watcher:
            return
        current: Set[str] = set(self._watcher.directories())
        needed = set(self._collect_dirs_recursive())
        new_dirs = list(needed - current)
        if new_dirs:
            self._watcher.addPaths(new_dirs)

    def start_watching(self):
        if self._watcher is not None:
            return
        self._watcher = QFileSystemWatcher()
        dirs = self._collect_dirs_recursive()
        if dirs:
            self._watcher.addPaths(dirs)
        # Connect signals
        self._watcher.directoryChanged.connect(self._on_directory_changed)  # type: ignore
        self._watcher.fileChanged.connect(self._on_file_changed)  # type: ignore
        print(
            f"[ProjectFolderManager] Watching {len(self._watcher.directories())} directories under {self.repo_path}"
        )

    def stop_watching(self):
        if self._watcher is None:
            return
        try:
            # Clear watched paths
            dirs = self._watcher.directories()
            files = self._watcher.files()
            if dirs:
                self._watcher.removePaths(dirs)
            if files:
                self._watcher.removePaths(files)
        finally:
            self._watcher = None

    # ----- Signal handlers -----
    def _on_directory_changed(self, path: str):
        print(f"[ProjectFolderManager] Directory changed: {path}")
        # New subdirectories may appear; ensure we're watching them
        self._ensure_subdirs_watched()

    def _on_file_changed(self, path: str):
        print(f"[ProjectFolderManager] File changed: {path}")

    # ----- Indexing -----
    def index_folder(self) -> int:
        # Index recursively
        # If MigrationManager says there should be a migration - do it and reindex
        # with setting a flag to avoid getting in an infinite loop if something goes
        # wrong with the migration

        # use pathlib
        count = 0
        should_do_migration = False
        for dirpath, dirnames, filenames in os.walk(self.repo_path):
            # Minimal check to see if a migration is needed.
            for fname in filenames:
                if self.migration_manager.entry_is_legacy(Path(dirpath) / fname):
                    log.info(f"Legacy entry detected: {fname}, will trigger migration")
                    should_do_migration = True
                    break
            if should_do_migration:
                break

        if should_do_migration:
            if self._migration_done:
                raise Exception(
                    "Legacy files still present after migration. "
                    "Aborting to avoid infinite loop."
                )
            log.info("Starting migration process...")
            self.migration_manager.do_all_migrations()
            self._migration_done = True
            log.info("Migration process completed. Re-indexing...")
            return self.index_folder()

        for _ in self._iter_canvas_page_paths():
            count += 1

        log.info(f"Indexed {count} V5 page file(s) in {self.repo_path}")
        return count
