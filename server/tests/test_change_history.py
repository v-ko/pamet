import pytest
from sivkit.libs.model import dump_to_dict
from sivkit.storage.change import Change
from sivkit.storage.commit import Commit
from sivkit.storage.delta import Delta
from sivkit.storage.hash_tree import build_hash_tree
from sivkit.storage.in_memory_store import InMemoryStore
from sivkit.storage.sqlite_vcs_adapter import SqliteVcsAdapter

from pamet.model.page import Page
from pamet.services.full_change_history_service import (
    FullChangeHistoryService,
    ParentMismatchError,
)


def _commit(store: InMemoryStore, page: Page, commit_id: str, parent_id: str) -> Commit:
    delta = Delta.from_changes([Change.create(page)])
    # Advance the project even if history later rejects this commit.
    store.apply_delta(delta)
    return Commit(
        id=commit_id,
        parent_id=parent_id,
        snapshot_hash=build_hash_tree(store).root_hash(),
        timestamp=0,
        message="test",
        delta_data=delta.asdict(),
    )


def test_append_and_reconcile_patch(tmp_path):
    db_path = tmp_path / "change-history.db"
    service = FullChangeHistoryService(db_path)
    project = InMemoryStore()

    # Reads and a no-op check don't create the database
    assert (
        service.verify_and_reconcile([], build_hash_tree(project).root_hash())[
            "head_id"
        ]
        == ""
    )
    assert service.get_commits(["x"]) == []
    assert service.commit_graph().branch_commits("main") == []
    assert not db_path.exists()

    assert service.append([_commit(project, Page(), "c1", "")]) == "c1"
    # A wrong parent leaves this page in the project but absent from history.
    rejected = Page()
    with pytest.raises(ParentMismatchError):
        service.append([_commit(project, rejected, "c2", "wrong")])

    # Store a valid delta with a deliberately incorrect snapshot hash.
    bad_hash = _commit(project, Page(), "c3", "c1")
    bad_hash.snapshot_hash = "0" * 64
    service.append([bad_hash])

    # Report c3's bad hash and patch only the page missed by the rejected c2.
    state = [dump_to_dict(e) for e in project.find()]
    project_hash = build_hash_tree(project).root_hash()
    result = service.verify_and_reconcile(state, project_hash)
    assert result["mismatches"] == 1
    assert not result["hashes_disagree"]
    [patch] = service.get_commits([result["head_id"]])
    assert patch.parent_id == "c3"
    assert patch.snapshot_hash == project_hash
    assert set(patch.delta_data) == {rejected.id}

    # Nothing left to patch
    assert service.verify_and_reconcile(state, project_hash)["head_id"] == patch.id

    # Matching raw records need no patch, even with fields unknown to Python.
    # The deliberately stale hash does not establish TS/Python hash parity.
    extra = {**dump_to_dict(Page()), "ts_only": 1}
    delta = Delta.from_changes([Change(extra["id"], {}, extra)])
    project.apply_delta(delta)
    project_hash = build_hash_tree(project).root_hash()
    service.append(
        [
            Commit(
                id="c4",
                parent_id=patch.id,
                snapshot_hash=project_hash,
                timestamp=0,
                message="test",
                delta_data=delta.asdict(),
            )
        ]
    )
    assert service.verify_and_reconcile([*state, extra], "stale")["head_id"] == "c4"
    service.close()


def test_reopen_history_loads_head_before_append(tmp_path):
    db_path = tmp_path / "change-history.db"
    project = InMemoryStore()
    service = FullChangeHistoryService(db_path)
    service.append([_commit(project, Page(), "c1", "")])
    service.close()

    # Reopening must restore c1 as the head before validating c2's parent.
    reopened_service = FullChangeHistoryService(db_path)
    assert reopened_service.get_commits(["c1"])[0].id == "c1"
    assert reopened_service.append([_commit(project, Page(), "c2", "c1")]) == "c2"
    reopened_service.close()


def test_reads_do_not_create_missing_branch(tmp_path):
    db_path = tmp_path / "change-history.db"
    # Unlike a missing database, this database exists but has no main branch.
    adapter = SqliteVcsAdapter(db_path)
    adapter.close()

    service = FullChangeHistoryService(db_path)
    assert service.get_commits([]) == []
    assert service.commit_graph().branch("main") is None
    empty_hash = build_hash_tree(InMemoryStore()).root_hash()
    assert service.verify_and_reconcile([], empty_hash)["head_id"] == ""
    assert service.verify_and_reconcile([], "stale")["hashes_disagree"]
    assert service.run_integrity(False, lambda progress: None)["total"] == 0
    assert service.run_integrity(True, lambda progress: None)["total"] == 0
    service.close()

    # Checks and repair must leave the missing branch uncreated on disk.
    adapter = SqliteVcsAdapter(db_path)
    assert adapter.get_commit_graph().branch("main") is None
    adapter.close()


def test_reconcile_creates_initial_patch_and_then_is_noop(tmp_path):
    db_path = tmp_path / "change-history.db"
    service = FullChangeHistoryService(db_path)
    page = Page()
    project = InMemoryStore()
    project.load_data([page])
    entities = [dump_to_dict(page)]
    project_hash = build_hash_tree(project).root_hash()

    # Seed absent history from the nonempty project with one root patch.
    result = service.verify_and_reconcile(entities, project_hash)
    assert db_path.exists()
    assert result["mismatches"] == 0
    assert not result["hashes_disagree"]
    [patch] = service.get_commits([result["head_id"]])
    assert patch.parent_id == ""
    assert patch.message == "History patch"
    assert patch.snapshot_hash == project_hash
    assert set(patch.delta_data) == {page.id}

    # Rechecking the same snapshot must not append another patch.
    assert service.verify_and_reconcile(entities, project_hash) == result
    assert len(service.commit_graph().branch_commits("main")) == 1
    service.close()


def test_hash_disagreement_without_changes_does_not_create_history(tmp_path):
    db_path = tmp_path / "change-history.db"
    service = FullChangeHistoryService(db_path)
    # A hash mismatch alone is not a data change worth creating history for.
    result = service.verify_and_reconcile([], "stale")
    assert result == {"head_id": "", "mismatches": 0, "hashes_disagree": True}
    assert not db_path.exists()
    service.close()
