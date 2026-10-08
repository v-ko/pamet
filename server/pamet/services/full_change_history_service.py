"""Change history: a copy of the project's commits in a separate SQLite repo.

The web app's storage worker appends commits and verifies and reconciles history
when recording starts, automatically committing any missing project changes.
All methods block; callers run them in worker threads.
One operation at a time per project.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from sivkit.libs.model import load_from_dict
from sivkit.storage.change import Change
from sivkit.storage.commit import Commit
from sivkit.storage.commit_graph import BranchMetadata, CommitGraph
from sivkit.storage.delta import Delta, squash_deltas
from sivkit.storage.hash_tree import build_hash_tree
from sivkit.storage.in_memory_store import InMemoryStore
from sivkit.storage.sqlite_vcs_adapter import SqliteVcsAdapter
from sivkit.storage.vcs_adapter import InternalRepoUpdate
from sivkit.storage.vcs_diagnostics import verify_or_fix_hashes
from sivkit.util import get_new_id

log = logging.getLogger(__name__)

BRANCH = "main"


class ParentMismatchError(Exception):
    pass


def _repository_update(
    added_commits: list[Commit] | None = None,
    added_branches: list[BranchMetadata] | None = None,
    updated_branches: list[BranchMetadata] | None = None,
) -> InternalRepoUpdate:
    return InternalRepoUpdate(
        added_commits=added_commits or [],
        removed_commits=[],
        updated_commits=[],
        added_branches=added_branches or [],
        updated_branches=updated_branches or [],
        removed_branches=[],
    )


class FullChangeHistoryService:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._lock = threading.Lock()
        self._adapter: SqliteVcsAdapter | None = None
        self._head_commit_id = ""
        self._closed = False
        # The running check-all / repair, for the 409.
        self.integrity_task: asyncio.Task | None = None

    @property
    def diagnostics_dir(self) -> Path:
        return self._db_path.parent

    def _load_existing_history(self) -> SqliteVcsAdapter | None:
        """Lazily load existing history without creating a database or branch."""
        if self._closed:
            raise RuntimeError("Change history is closed")
        if self._adapter is None:
            if not self._db_path.exists():
                return None
            adapter = SqliteVcsAdapter(self._db_path)
            branch = adapter.get_commit_graph().branch(BRANCH)
            if branch is not None:
                self._head_commit_id = branch.head_commit_id or ""
            self._adapter = adapter
        return self._adapter

    def _ensure_history_created(self) -> SqliteVcsAdapter:
        """Lazily create the database and main branch before writing history."""
        adapter = self._load_existing_history()
        if adapter is None:
            adapter = SqliteVcsAdapter(self._db_path)
            self._adapter = adapter
        if adapter.get_commit_graph().branch(BRANCH) is None:
            adapter.apply_update(
                _repository_update(added_branches=[BranchMetadata(BRANCH, None)])
            )
        return adapter

    def _append_commits(self, adapter: SqliteVcsAdapter, commits: list[Commit]) -> None:
        expected_parent_id = self._head_commit_id
        for commit in commits:
            if commit.parent_id != expected_parent_id:
                raise ParentMismatchError(
                    f"Commit {commit.id} has parent {commit.parent_id!r}, "
                    f"expected {expected_parent_id!r}"
                )
            expected_parent_id = commit.id
        adapter.apply_update(
            _repository_update(
                added_commits=commits,
                updated_branches=[BranchMetadata(BRANCH, expected_parent_id)],
            )
        )
        self._head_commit_id = expected_parent_id

    def append(self, commits: list[Commit]) -> str:
        """Append commits on top of the head. Returns the new head id."""
        with self._lock:
            adapter = self._ensure_history_created()
            self._append_commits(adapter, commits)
            return self._head_commit_id

    def _verify_stored_hashes(
        self, adapter: SqliteVcsAdapter | None
    ) -> tuple[int, str]:
        """Verify history hashes, or return the empty-store hash when adapter is None."""
        mismatch_count = 0
        computed_head_hash = None
        if adapter is not None:
            for progress in verify_or_fix_hashes(adapter, BRANCH, fix=False):
                if progress.status == "mismatch_reported":
                    mismatch_count += 1
                if progress.computed_hash is not None:
                    computed_head_hash = progress.computed_hash
        if computed_head_hash is None:
            computed_head_hash = build_hash_tree(InMemoryStore()).root_hash()
        return mismatch_count, computed_head_hash

    def _calculate_reconciliation_delta(
        self,
        adapter: SqliteVcsAdapter | None,
        commit_ids: list[str],
        entities: list[dict[str, Any]],
    ) -> Delta:
        """Diff raw entity dictionaries, preserving fields unknown to Python models."""
        history_deltas = []
        if adapter is not None and commit_ids:
            history_deltas = [
                commit.delta_data or {} for commit in adapter.get_commits(commit_ids)
            ]
        reconciliation_delta = squash_deltas(history_deltas).reversed()
        target_delta = Delta.from_changes(
            [Change(entity["id"], {}, dict(entity)) for entity in entities]
        )
        reconciliation_delta.merge_with_priority(target_delta)
        return reconciliation_delta

    def _build_reconciliation_commit(
        self, delta: Delta, entities: list[dict[str, Any]]
    ) -> Commit:
        """Hash the target using the same Python models as history verification."""
        target_store = InMemoryStore()
        target_store.load_data([load_from_dict(dict(entity)) for entity in entities])
        return Commit(
            id=get_new_id(),
            parent_id=self._head_commit_id,
            snapshot_hash=build_hash_tree(target_store).root_hash(),
            timestamp=int(time.time() * 1000),
            message="History patch",
            delta_data=delta.asdict(),
        )

    def verify_and_reconcile(
        self, entities: list[dict[str, Any]], snapshot_hash: str
    ) -> dict:
        """Verify stored hashes and automatically append a History patch if needed."""
        with self._lock:
            adapter = self._load_existing_history()
            graph = adapter.get_commit_graph() if adapter is not None else None
            history = (
                adapter
                if graph is not None and graph.branch(BRANCH) is not None
                else None
            )
            mismatch_count, computed_head_hash = self._verify_stored_hashes(history)
            hashes_disagree = False
            if computed_head_hash != snapshot_hash:
                commit_ids = (
                    [commit.id for commit in graph.branch_commits(BRANCH)]
                    if graph is not None and history is not None
                    else []
                )
                reconciliation_delta = self._calculate_reconciliation_delta(
                    history, commit_ids, entities
                )
                if reconciliation_delta.is_empty():
                    hashes_disagree = True
                else:
                    adapter = self._ensure_history_created()
                    patch = self._build_reconciliation_commit(
                        reconciliation_delta, entities
                    )
                    self._append_commits(adapter, [patch])
                    hashes_disagree = patch.snapshot_hash != snapshot_hash
                    log.info("Patched change history with %s", patch.id)
            return {
                "head_id": self._head_commit_id,
                "mismatches": mismatch_count,
                "hashes_disagree": hashes_disagree,
            }

    def commit_graph(self) -> CommitGraph:
        with self._lock:
            adapter = self._load_existing_history()
            if adapter is None:
                graph = CommitGraph()
                graph.create_branch(BRANCH)
                return graph
            return adapter.get_commit_graph()

    def get_commits(self, ids: list[str]) -> list[Commit]:
        with self._lock:
            adapter = self._load_existing_history()
            return adapter.get_commits(ids) if adapter is not None else []

    def run_integrity(self, fix: bool, on_progress: Callable[[dict], None]) -> dict:
        """Check (or repair) every hash, write a log file, return a summary."""
        with self._lock:
            adapter = self._load_existing_history()
            mismatch_status = "mismatch_fixed" if fix else "mismatch_reported"
            total_commits = 0
            mismatch_commits: list[dict] = []
            progress_events = (
                verify_or_fix_hashes(adapter, BRANCH, fix=fix)
                if adapter is not None
                and adapter.get_commit_graph().branch(BRANCH) is not None
                else []
            )
            for progress in progress_events:
                total_commits = progress.total_commits
                if progress.status == mismatch_status:
                    mismatch_commits.append(
                        {
                            "index": progress.commit_index,
                            "commit_id": progress.commit_id,
                            "computed_hash": progress.computed_hash,
                            "stored_hash": progress.stored_hash,
                            "delta_data": progress.delta_data,
                            "parent_id": progress.parent_id,
                            "timestamp": progress.timestamp,
                            "message": progress.message,
                        }
                    )
                on_progress(
                    {
                        "type": "progress",
                        "index": progress.commit_index,
                        "total": progress.total_commits,
                        "status": progress.status,
                        "commit_id": progress.commit_id,
                        "computed_hash": progress.computed_hash,
                        "stored_hash": progress.stored_hash,
                    }
                )
            if fix and adapter is not None:
                # A repair can remove the head commit.
                branch = adapter.get_commit_graph().branch(BRANCH)
                self._head_commit_id = ""
                if branch is not None:
                    self._head_commit_id = branch.head_commit_id or ""

            operation = "repair-hashes" if fix else "check-all"
            count_field = "fixed" if fix else "mismatches"
            summary = {"total": total_commits, count_field: len(mismatch_commits)}
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_path = self.diagnostics_dir / f"integrity-{operation}-{timestamp}.json"
            log_path.write_text(
                json.dumps(
                    {**summary, "mismatch_commits": mismatch_commits},
                    indent=2,
                    default=str,
                )
            )
            return {**summary, "log_path": str(log_path.resolve())}

    def close(self) -> None:
        with self._lock:
            self._closed = True
            if self._adapter is not None:
                self._adapter.close()
                self._adapter = None
        log.info("FullChangeHistoryService closed (db: %s)", self._db_path)
