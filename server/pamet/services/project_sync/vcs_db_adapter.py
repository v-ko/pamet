from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from peewee import (
    CharField,
    IntegerField,
    Model,
    SqliteDatabase,
    TextField,
)


def _infer_repo_changes_from_graphs(
    local_graph: dict[str, Any], remote_graph: dict[str, Any]
) -> dict[str, Any]:
    local_commits = local_graph["commits"]
    remote_commits = remote_graph["commits"]

    local_commits_by_id = {commit["id"]: commit for commit in local_commits}
    remote_commits_by_id = {commit["id"]: commit for commit in remote_commits}

    local_ids = set(local_commits_by_id)
    remote_ids = set(remote_commits_by_id)

    removed_commits = [commit for commit in local_commits if commit["id"] not in remote_ids]
    added_commits = [commit for commit in remote_commits if commit["id"] not in local_ids]
    updated_commits = []
    for commit in remote_commits:
        local_commit = local_commits_by_id.get(commit["id"])
        if local_commit is None:
            continue
        if (
            local_commit["parentId"] != commit["parentId"]
            or local_commit["snapshotHash"] != commit["snapshotHash"]
        ):
            updated_commits.append(commit)

    local_branches = local_graph["branches"]
    remote_branches = remote_graph["branches"]
    local_branches_by_name = {branch["name"]: branch for branch in local_branches}
    remote_branches_by_name = {branch["name"]: branch for branch in remote_branches}

    removed_branches = [
        branch for branch in local_branches if branch["name"] not in remote_branches_by_name
    ]
    added_branches = [
        branch for branch in remote_branches if branch["name"] not in local_branches_by_name
    ]
    updated_branches = []
    for branch in remote_branches:
        local_branch = local_branches_by_name.get(branch["name"])
        if local_branch is None:
            continue
        if local_branch["headCommitId"] != branch["headCommitId"]:
            updated_branches.append(branch)

    return {
        "addedCommits": added_commits,
        "removedCommits": removed_commits,
        "updatedCommits": updated_commits,
        "addedBranches": added_branches,
        "updatedBranches": updated_branches,
        "removedBranches": removed_branches,
    }


def _sanity_check_and_hydrate_repo_update(
    repo_update: dict[str, Any],
    upserted_commits: list[dict[str, Any]],
) -> dict[str, Any]:
    added_ids = {commit["id"] for commit in repo_update["addedCommits"]}
    updated_ids = {commit["id"] for commit in repo_update["updatedCommits"]}

    hydrated_added: list[dict[str, Any]] = []
    hydrated_updated: list[dict[str, Any]] = []
    unmatched: list[str] = []

    for commit in upserted_commits:
        commit_id = commit["id"]
        if commit_id in added_ids:
            hydrated_added.append(commit)
            added_ids.remove(commit_id)
        elif commit_id in updated_ids:
            hydrated_updated.append(commit)
            updated_ids.remove(commit_id)
        else:
            unmatched.append(commit_id)

    if unmatched:
        raise ValueError(f"Unmatched upserted commits: {', '.join(unmatched)}")
    if added_ids:
        raise ValueError(
            f"Missing upserted commits for added ids: {', '.join(sorted(added_ids))}"
        )
    if updated_ids:
        raise ValueError(
            f"Missing upserted commits for updated ids: {', '.join(sorted(updated_ids))}"
        )

    return {
        "addedCommits": hydrated_added,
        "removedCommits": repo_update["removedCommits"],
        "updatedCommits": hydrated_updated,
        "addedBranches": repo_update["addedBranches"],
        "updatedBranches": repo_update["updatedBranches"],
        "removedBranches": repo_update["removedBranches"],
    }


class VcsBranchPW(Model):
    name = CharField(primary_key=True)
    head_commit_id = CharField(null=True)


class VcsCommitPW(Model):
    id = CharField(primary_key=True)
    parent_id = CharField()
    snapshot_hash = CharField()
    timestamp = IntegerField()
    message = TextField()
    delta_json = TextField()


class VcsDbAdapter:
    def __init__(self, repo_root: Path):
        self.repo_root = Path(repo_root)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = SqliteDatabase(str(self.db_path))
        self._ensure_schema()

    @property
    def db_path(self) -> Path:
        return self.repo_root / ".pamet" / "vcs.db"

    def _ensure_schema(self) -> None:
        with self._db.bind_ctx([VcsBranchPW, VcsCommitPW]):
            self._db.create_tables([VcsCommitPW, VcsBranchPW], safe=True)

    def _upsert_commit(self, commit: dict[str, Any]) -> None:
        with self._db.bind_ctx([VcsCommitPW]):
            (
                VcsCommitPW.insert(
                    id=commit["id"],
                    parent_id=commit["parentId"],
                    snapshot_hash=commit["snapshotHash"],
                    timestamp=commit["timestamp"],
                    message=commit["message"],
                    delta_json=json.dumps(commit["deltaData"]),
                )
                .on_conflict(
                    conflict_target=[VcsCommitPW.id],
                    update={
                        VcsCommitPW.parent_id: commit["parentId"],
                        VcsCommitPW.snapshot_hash: commit["snapshotHash"],
                        VcsCommitPW.timestamp: commit["timestamp"],
                        VcsCommitPW.message: commit["message"],
                        VcsCommitPW.delta_json: json.dumps(commit["deltaData"]),
                    },
                )
                .execute()
            )

    def _upsert_branch(self, branch: dict[str, Any]) -> None:
        with self._db.bind_ctx([VcsBranchPW]):
            (
                VcsBranchPW.insert(
                    name=branch["name"],
                    head_commit_id=branch["headCommitId"],
                )
                .on_conflict(
                    conflict_target=[VcsBranchPW.name],
                    update={VcsBranchPW.head_commit_id: branch["headCommitId"]},
                )
                .execute()
            )

    def ensure_branch(self, branch_name: str) -> None:
        normalized_branch_name = str(branch_name).strip()
        if not normalized_branch_name:
            raise ValueError("branch_name is required")
        with self._db.bind_ctx([VcsBranchPW]):
            (
                VcsBranchPW.insert(name=normalized_branch_name, head_commit_id=None)
                .on_conflict_ignore()
                .execute()
            )

    def get_commit_graph(self) -> dict[str, Any]:
        with self._db.bind_ctx([VcsBranchPW, VcsCommitPW]):
            branch_rows = list(VcsBranchPW.select().order_by(VcsBranchPW.name))
            commit_rows = list(
                VcsCommitPW.select().order_by(VcsCommitPW.timestamp.asc(), VcsCommitPW.id.asc())
            )

        return {
            "branches": [
                {
                    "name": row.name,
                    "headCommitId": row.head_commit_id,
                }
                for row in branch_rows
            ],
            "commits": [
                {
                    "id": row.id,
                    "parentId": row.parent_id,
                    "snapshotHash": row.snapshot_hash,
                    "timestamp": row.timestamp,
                    "message": row.message,
                }
                for row in commit_rows
            ],
        }

    def get_commits(self, ids: list[str]) -> list[dict[str, Any]]:
        if not ids:
            return []

        with self._db.bind_ctx([VcsCommitPW]):
            rows = list(VcsCommitPW.select().where(VcsCommitPW.id.in_(ids)))

        commit_by_id = {
            row.id: {
                "id": row.id,
                "parentId": row.parent_id,
                "snapshotHash": row.snapshot_hash,
                "timestamp": row.timestamp,
                "message": row.message,
                "deltaData": json.loads(row.delta_json),
            }
            for row in rows
        }

        missing_ids = [commit_id for commit_id in ids if commit_id not in commit_by_id]
        if missing_ids:
            raise ValueError(f"Missing commits: {', '.join(missing_ids)}")

        return [commit_by_id[commit_id] for commit_id in ids]

    def apply_repo_update(self, update_data: dict[str, Any]) -> None:
        raw_commit_graph = update_data.get("commitGraph")
        raw_upserted_commits = update_data.get("upsertedCommits")
        remote_graph = raw_commit_graph
        upserted_commits = raw_upserted_commits
        local_graph = self.get_commit_graph()
        repo_update = _infer_repo_changes_from_graphs(local_graph, remote_graph)
        hydrated_update = _sanity_check_and_hydrate_repo_update(repo_update, upserted_commits)

        with self._db.bind_ctx([VcsBranchPW, VcsCommitPW]):
            with self._db.atomic():
                for branch in hydrated_update["removedBranches"]:
                    VcsBranchPW.delete().where(VcsBranchPW.name == branch["name"]).execute()

                for commit in hydrated_update["removedCommits"]:
                    VcsCommitPW.delete().where(VcsCommitPW.id == commit["id"]).execute()

                for commit in hydrated_update["updatedCommits"]:
                    self._upsert_commit(commit)

                for commit in hydrated_update["addedCommits"]:
                    self._upsert_commit(commit)

                for branch in hydrated_update["addedBranches"]:
                    self._upsert_branch(branch)

                for branch in hydrated_update["updatedBranches"]:
                    self._upsert_branch(branch)
