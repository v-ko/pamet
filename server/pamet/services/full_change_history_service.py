"""Full change history service.

Receives deltas from the frontend (via a WebSocketSyncService in
*receiver* role) and commits each one to a dedicated SQLite-backed
Repository.  This gives a per-action commit history that can later be
queried for replay / visualization.
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import Any

from fusion import Entity
from fusion.logging import get_logger
from fusion.storage.base_store import Store
from fusion.storage.change import Change
from fusion.storage.delta import Delta
from fusion.storage.repository import (
    EmptyRepositoryError,
    MissingBranchError,
    Repository,
)
from fusion.storage.sqlite_vcs_adapter import SqliteVcsAdapter
from fusion.storage.ws_sync_service import WebSocketSyncService

log = get_logger(__name__)


class _CommittingStoreAdapter(Store):
    """Minimal Store adapter that commits to a Repository instead of
    holding entities in memory.

    HACK: WebSocketSyncService expects a Store.  For the normal use
    case (config sync) a real InMemoryStore is passed and everything
    works.  FullChangeHistoryService doesn't need a live store — it
    only needs to commit deltas.  This adapter quacks like a Store so
    the WS sync service can call clear/load_data/apply_delta/find on
    it, but under the hood each mutation becomes a repository commit.

    - ``find()`` delegates to ``repo.head_store`` (the repo already
      maintains an up-to-date in-memory snapshot).
    - ``load_data()`` diffs the received entities against the repo's
      head store and commits a seed delta.
    - ``apply_delta()`` commits the delta to the repo.
    - ``clear()`` is a no-op — the repo head store is the source of
      truth and is never wiped.
    """

    def __init__(self, repo: Repository) -> None:
        super().__init__()
        self._repo = repo

    # -- read operations (delegate to head_store) --------------------------

    def find(self, **filter: Any) -> Generator[Any, None, None]:
        yield from self._repo.head_store.find(**filter)

    def find_one(self, **filter: Any) -> Any | None:
        return self._repo.head_store.find_one(**filter)

    # -- mutations → repo commits ------------------------------------------

    def clear(self) -> None:
        # No-op: the repo head store is authoritative.
        # Reset _loaded so load_data can be called again on reconnect.
        self._loaded = False

    def load_data(self, entities: list[Entity], origin: str | None = None) -> Delta:
        """Diff received entities against repo head and commit a seed."""
        self._loaded = True

        received = {e.id: e for e in entities}
        head_entities = {e.id: e for e in self._repo.head_store.find()}

        changes: list[Change] = []

        for eid, entity in received.items():
            if eid not in head_entities:
                changes.append(Change.create(entity))
            else:
                change = Change.update(head_entities[eid], entity)
                if not change.is_empty():
                    changes.append(change)

        for eid, entity in head_entities.items():
            if eid not in received:
                changes.append(Change.delete(entity))

        if changes:
            seed_delta = Delta.from_changes(changes)
            try:
                self._repo.commit(seed_delta, message="sync-seed")
                log.info(
                    "CommittingStoreAdapter: seeded repo with %d changes",
                    len(changes),
                )
            except Exception as e:
                log.error("CommittingStoreAdapter: failed to seed repo: %s", e)
            return seed_delta
        else:
            log.info("CommittingStoreAdapter: repo already in sync")
            return Delta()

    def apply_delta(self, delta: Delta, origin: str | None = None) -> Delta:
        """Commit a delta to the repository."""
        if delta.is_empty():
            return delta

        try:
            commit = self._repo.commit(delta, message="user-action")
            log.info(
                "CommittingStoreAdapter: committed %s (%d changes)",
                commit.id,
                len(list(delta.changes())),
            )
        except Exception as e:
            log.error("CommittingStoreAdapter: failed to commit delta: %s", e)
        return delta

    # -- unused but required by Store interface ----------------------------

    def insert_one(self, entity: Entity) -> Change:
        raise NotImplementedError("Use load_data or apply_delta")

    def update_one(self, entity: Entity) -> Change:
        raise NotImplementedError("Use apply_delta")

    def remove_one(self, entity: Entity) -> Change:
        raise NotImplementedError("Use apply_delta")


class FullChangeHistoryService:
    """Wraps a Repository + SqliteVcsAdapter behind a WS sync receiver.

    Lifecycle:
        1. Constructed with a DB path.
        2. ``ws_sync_service.run(send, receive)`` is awaited on the WS
           endpoint — this triggers the handshake (full_state) and then
           streams deltas.
        3. Each delta is committed to the repository.
        4. ``close()`` tears down the adapter.
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

        # Persistent storage
        self._adapter = SqliteVcsAdapter(db_path)

        # Repository — open existing or create new
        try:
            self._repo = Repository.open(self._adapter, branch_name="main")
        except (EmptyRepositoryError, MissingBranchError):
            self._repo = Repository.create(self._adapter, branch_name="main")

        self._store_adapter = _CommittingStoreAdapter(self._repo)
        self._ws_sync = WebSocketSyncService(self._store_adapter, role="receiver")

    @property
    def ws_sync_service(self) -> WebSocketSyncService:
        return self._ws_sync

    @property
    def repository(self) -> Repository:
        return self._repo

    def close(self) -> None:
        self._adapter.close()
        log.info("FullChangeHistoryService closed (db: %s)", self._db_path)
