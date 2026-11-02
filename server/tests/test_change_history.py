import asyncio
import threading

import pytest
from sivkit.libs.model import dump_to_dict
from sivkit.storage.change import Change
from sivkit.storage.commit import Commit
from sivkit.storage.delta import Delta
from sivkit.storage.hash_tree import build_hash_tree
from sivkit.storage.in_memory_store import InMemoryStore
from sivkit.storage.sqlite_vcs_adapter import SqliteVcsAdapter
from sivkit.storage.vcs_diagnostics import HashCheckProgress

from pamet.model.page import Page
from pamet.services import full_change_history_service as history_module
from pamet.services.full_change_history_service import (
    FullChangeHistoryService,
    HistoryCheckInProgressError,
    HistoryClosedError,
    HistoryVerificationError,
    IntegrityRunningError,
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


def test_recording_and_recovery(tmp_path):
    async def check():
        db_path = tmp_path / "change-history.db"
        service = FullChangeHistoryService(db_path)
        project = InMemoryStore()
        project.insert_one(Page())
        state = [dump_to_dict(e) for e in project.find()]
        project_hash = build_hash_tree(project).root_hash()

        # Enabling recording seeds history; rechecking an unchanged project is a no-op.
        seed = await service.verify_and_reconcile(state, project_hash)
        assert seed["head_id"] and seed["mismatches"] == 0
        assert not seed["hashes_disagree"]
        assert await service.verify_and_reconcile(state, project_hash) == seed
        await service.append([_commit(project, Page(), "c1", seed["head_id"])])

        # A rejected append leaves a gap; a corrupt hash is reported separately.
        missing = Page()
        with pytest.raises(ParentMismatchError):
            await service.append([_commit(project, missing, "c2", "wrong")])
        bad_hash = _commit(project, Page(), "c3", "c1")
        bad_hash.snapshot_hash = "0" * 64
        await service.append([bad_hash])
        state = [dump_to_dict(e) for e in project.find()]
        project_hash = build_hash_tree(project).root_hash()
        result = await service.verify_and_reconcile(state, project_hash)
        assert result["mismatches"] == 1 and not result["hashes_disagree"]
        [patch] = await service.get_commits([result["head_id"]])
        assert patch.parent_id == "c3" and set(patch.delta_data) == {missing.id}
        assert patch.snapshot_hash == project_hash
        assert await service.verify_and_reconcile(state, project_hash) == result

        # Explicit repair fixes the hash; reconciliation alone must not conceal it.
        repair = await service.start_integrity(True, lambda _: None)
        assert repair["fixed"] == 1
        assert (await service.verify_and_reconcile(state, project_hash))[
            "mismatches"
        ] == 0
        await service.close()

        # Reopening restores the head and preserves readable, ordered history.
        service = FullChangeHistoryService(db_path)
        last = _commit(project, Page(), "c4", patch.id)
        await service.append([last])
        first, has_more = await service.get_commits_page("main", None, 2)
        assert [commit.id for commit in first] == [seed["head_id"], "c1"] and has_more
        rest, has_more = await service.get_commits_page("main", "c1", 10)
        assert [commit.id for commit in rest] == ["c3", patch.id, "c4"] and not has_more
        # Malformed history is reported without an implicit repair.
        bad = Commit(
            "bad", last.id, last.snapshot_hash, 0, "duplicate create", last.delta_data
        )
        await service.append([bad])
        with pytest.raises(HistoryVerificationError, match="already exists"):
            await service.verify_and_reconcile(
                [dump_to_dict(e) for e in project.find()],
                build_hash_tree(project).root_hash(),
            )
        assert (await service.commit_graph()).branch("main").head_commit_id == bad.id
        assert [c.asdict() for c in await service.get_commits([last.id, bad.id])] == [
            last.asdict(),
            bad.asdict(),
        ]
        await service.close()

    asyncio.run(check())


@pytest.mark.parametrize("existing_db", [False, True], ids=["absent", "empty"])
def test_unused_history_stays_unwritten(tmp_path, existing_db):
    async def check():
        db_path = tmp_path / "change-history.db"
        if existing_db:
            SqliteVcsAdapter(db_path).close()
        service = FullChangeHistoryService(db_path)
        assert await service.get_commits([]) == []
        empty_hash = build_hash_tree(InMemoryStore()).root_hash()
        assert (await service.verify_and_reconcile([], empty_hash))["head_id"] == ""
        mismatch = await service.verify_and_reconcile([], "stale")
        assert mismatch["head_id"] == "" and mismatch["hashes_disagree"]
        if existing_db:
            assert (await service.start_integrity(True, lambda _: None))["total"] == 0
            assert (await service.commit_graph()).branch("main") is None
        await service.close()
        assert db_path.exists() == existing_db

    asyncio.run(check())


@pytest.mark.parametrize("integrity_fails", [False, True])
def test_history_shutdown(tmp_path, monkeypatch, integrity_fails):
    async def check():
        service = FullChangeHistoryService(tmp_path / "history.db")
        loop = asyncio.get_running_loop()
        started = asyncio.Event()
        release = threading.Event()
        order = []

        def integrity(fix, on_progress, cancel=None):
            loop.call_soon_threadsafe(started.set)
            assert release.wait(5), "integrity worker timed out"
            order.append("integrity")
            if integrity_fails:
                raise OSError("integrity failed after disconnect")
            return {"total": 0}

        append_commits = service._append

        def append_after(commits):
            order.append("append")
            return append_commits(commits)

        monkeypatch.setattr(service, "_run_integrity", integrity)
        monkeypatch.setattr(service, "_append", append_after)
        result = service.start_integrity(False, lambda _: None)
        await asyncio.wait_for(started.wait(), 5)
        result.cancel()
        with pytest.raises(IntegrityRunningError):
            service.start_integrity(False, lambda _: None)

        commit = _commit(InMemoryStore(), Page(), "c1", "")
        append = asyncio.create_task(service.append([commit]))
        await asyncio.sleep(0)
        assert not append.done()
        append.cancel()
        with pytest.raises(asyncio.CancelledError):
            await append

        closing = asyncio.create_task(service.close())
        await asyncio.sleep(0)
        with pytest.raises(HistoryClosedError):
            await service.commit_graph()
        release.set()
        await asyncio.wait_for(closing, 5)
        assert order == ["integrity", "append"]

        # Neither a disconnected caller nor a failed earlier job loses the append.
        reopened = FullChangeHistoryService(tmp_path / "history.db")
        assert [commit.id for commit in await reopened.get_commits(["c1"])] == ["c1"]
        await reopened.close()

    asyncio.run(check())


def test_history_retry_and_close_preserve_recorded_edits(tmp_path, monkeypatch):
    async def check():
        service = FullChangeHistoryService(tmp_path / "history.db")
        project = InMemoryStore()
        commit = _commit(project, Page(), "c1", "")
        await service.append([commit])
        state = [dump_to_dict(e) for e in project.find()]
        started, release = asyncio.Event(), threading.Event()
        loop = asyncio.get_running_loop()
        replays = []

        def replay(*args, **kwargs):
            replays.append(commit.id)
            loop.call_soon_threadsafe(started.set)
            assert release.wait(5)
            yield HashCheckProgress(0, 1, commit.id, "ok", commit.snapshot_hash)

        monkeypatch.setattr(history_module, "verify_or_fix_hashes", replay)
        try:
            # A disconnected caller's retry shares its unfinished check.
            request = asyncio.create_task(
                service.verify_and_reconcile(state, commit.snapshot_hash)
            )
            await asyncio.wait_for(started.wait(), 5)
            request.cancel()
            with pytest.raises(asyncio.CancelledError):
                await request
            retry = asyncio.create_task(
                service.verify_and_reconcile(state, commit.snapshot_hash)
            )
            await asyncio.sleep(0)
            with pytest.raises(HistoryCheckInProgressError):
                await service.verify_and_reconcile(state, "different snapshot")
            release.set()
            assert (await asyncio.wait_for(retry, 5))["head_id"] == commit.id
            assert replays == [commit.id]

            # Closing a later check stops real replay at its next boundary.
            started.clear()
            release.clear()
            request = asyncio.create_task(
                service.verify_and_reconcile(state, commit.snapshot_hash)
            )
            await asyncio.wait_for(started.wait(), 5)
            closing = asyncio.create_task(service.close())
            await asyncio.sleep(0)
            release.set()
            await asyncio.wait_for(closing, 5)
            with pytest.raises(HistoryClosedError):
                await request
        finally:
            release.set()
            await service.close()

        reopened = FullChangeHistoryService(tmp_path / "history.db")
        assert [item.id for item in await reopened.get_commits([commit.id])] == [
            commit.id
        ]
        await reopened.close()

    asyncio.run(check())
