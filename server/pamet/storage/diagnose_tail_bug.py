"""Diagnose the tail-anchor regression in the backward pipeline.

This script reproduces the specific change_splitter call that processes the
git diff containing note 63fcd3bf-4c36c9ff and its 11 arrows, and traces
which sub-group each entity ends up in.

It proves whether the note and arrows are in the SAME source git diff and
shows how the splitter separates them into different sub-groups.

Usage:
    cd /sync/projects/misli/pamet/server
    python -m pamet.storage.diagnose_tail_bug
"""

from __future__ import annotations

import sys
from collections import defaultdict
from datetime import date, datetime, time, timezone
from pathlib import Path

from sivkit.libs.model import dump_to_dict, load_from_dict
from sivkit.storage.change import Change
from sivkit.storage.delta import Delta
from sivkit.storage.in_memory_store import InMemoryStore
from sivkit.storage.sqlite_vcs_adapter import SqliteVcsAdapter

import pamet  # register entity types
from pamet.model.arrow import Arrow
from pamet.model.note import Note
from pamet.storage.change_splitter import (
    _entity_modified_dt,
    infer_deltas_between_stores,
)

# Target entities
TARGET_NOTE = "63fcd3bf-4c36c9ff"
TARGET_ARROWS = [
    "63fcd3bf-c705f59f",
    "63fcd3bf-5597f588",
    "63fcd3bf-8f0dedf4",
    "63fcd3bf-7d15ba9b",
    "63fcd3bf-6b9e69ec",
    "63fcd3bf-98269023",
    "63fcd3bf-28ea3030",
    "63fcd3bf-ca27a86a",
    "63fcd3bf-492f68f9",
    "63fcd3bf-0536d839",
    "63fcd3bf-7e6ab62e",
]
ALL_TARGETS = {TARGET_NOTE} | set(TARGET_ARROWS)

LIVE_VCS_DB = Path("/sync/pamet/repo/.pamet/change-history.db")


def find_source_diff():
    """Find which git diff(s) contain changes to the target entities."""
    print("=" * 70)
    print("STEP 1: Find which commit deltas contain the target entities")
    print("=" * 70)

    db = SqliteVcsAdapter(LIVE_VCS_DB)
    graph = db.get_commit_graph()
    commits = graph.branch_commits("main")

    # Find all commits that touch our target entities
    note_commits = []
    arrow_commits: dict[str, list] = defaultdict(list)

    for i, cm in enumerate(commits[:500]):
        c = db.get_commit(cm.id)
        if c and c.delta_data:
            delta = Delta.from_data(c.delta_data)
            for ch in delta.changes():
                if ch.entity_id == TARGET_NOTE:
                    note_commits.append((i, c.message, ch.type().name))
                elif ch.entity_id in ALL_TARGETS:
                    arrow_commits[ch.entity_id].append((i, c.message, ch.type().name))

    print(f"\nNote {TARGET_NOTE}:")
    for idx, msg, ctype in note_commits:
        print(f"  commit {idx}: {ctype} — {msg[:80]}")

    print(f"\nArrows ({len(arrow_commits)} found):")
    # Group by commit for compactness
    arrow_by_commit: dict[int, list] = defaultdict(list)
    for aid, entries in arrow_commits.items():
        for idx, msg, ctype in entries:
            arrow_by_commit[idx].append((aid, ctype))

    for idx in sorted(arrow_by_commit):
        entries = arrow_by_commit[idx]
        c = db.get_commit(commits[idx].id)
        print(
            f"  commit {idx}: {len(entries)} arrows "
            f"({entries[0][1]}) — {c.message[:80]}"
        )

    # Check if note and arrows share the same source git commit message
    note_sources = set(msg for _, msg, _ in note_commits)
    arrow_sources = set()
    for entries in arrow_commits.values():
        for _, msg, _ in entries:
            arrow_sources.add(msg)

    print(f"\nNote source messages: {note_sources}")
    print(f"Arrow source messages: {arrow_sources}")

    if note_sources & arrow_sources:
        print("\n*** NOTE AND ARROWS SHARE A SOURCE DIFF ***")
    else:
        print("\n*** NOTE AND ARROWS ARE IN DIFFERENT SOURCE DIFFS ***")

    return db, commits


def trace_splitter_assignment():
    """Reproduce the splitter call and trace sub-group assignments."""
    print("\n" + "=" * 70)
    print("STEP 2: Reproduce the splitter logic and trace assignments")
    print("=" * 70)

    db = SqliteVcsAdapter(LIVE_VCS_DB)
    graph = db.get_commit_graph()
    commits = graph.branch_commits("main")

    # We need to find the diff that contains both note DELETE and arrow DELETEs.
    # First, let's find the commit where the note is deleted and get the source
    # git diff info from the message.
    # From STEP 1 we know: note DELETE is at commit 2,
    # msg='git:2013-02-23:219ch... sub:177/178 ... | 2014.03.15'
    # This means the git diff for '2014.03.15' was split into 178 sub-groups.
    # Let's find ALL commits from that same git diff.

    # The source git message is '2014.03.15' — find all commits from this diff
    source_commits = []
    for i, cm in enumerate(commits[:500]):
        c = db.get_commit(cm.id)
        if c and "2014.03.15" in c.message and c.message.startswith("git:"):
            source_commits.append((i, c))

    print(f"\nCommits from '2014.03.15' git diff: {len(source_commits)}")
    if source_commits:
        print(
            f"  First: commit {source_commits[0][0]} — {source_commits[0][1].message[:70]}"
        )
        print(
            f"  Last:  commit {source_commits[-1][0]} — {source_commits[-1][1].message[:70]}"
        )

    # Now check: are the arrow DELETEs within these commits?
    arrow_delete_commits = set()
    for i, cm in enumerate(commits[:500]):
        c = db.get_commit(cm.id)
        if c and c.delta_data:
            delta = Delta.from_data(c.delta_data)
            for ch in delta.changes():
                if ch.entity_id in set(TARGET_ARROWS) and ch.type().name == "DELETE":
                    arrow_delete_commits.add(i)

    source_range = set(i for i, _ in source_commits)
    arrows_in_source = arrow_delete_commits & source_range
    arrows_outside = arrow_delete_commits - source_range

    print(f"\nArrow DELETE commits within '2014.03.15' diff: {arrows_in_source}")
    print(f"Arrow DELETE commits OUTSIDE '2014.03.15' diff: {arrows_outside}")

    if arrows_outside:
        # The arrows are in a different diff — this is a cross-diff issue
        for idx in sorted(arrows_outside):
            c = db.get_commit(commits[idx].id)
            print(f"  commit {idx}: {c.message[:80]}")


def trace_splitter_internals():
    """Instrument the splitter to show exactly where each target ends up."""
    print("\n" + "=" * 70)
    print("STEP 3: Trace splitter internals for the target diff")
    print("=" * 70)
    print("\nRebuilding the stores for the '2014.03.15' git diff...")

    db = SqliteVcsAdapter(LIVE_VCS_DB)
    graph = db.get_commit_graph()
    commits = graph.branch_commits("main")

    # Find all commits from '2014.03.15' git diff
    source_commits_idx = []
    for i, cm in enumerate(commits[:500]):
        c = db.get_commit(cm.id)
        if c and "2014.03.15" in c.message and c.message.startswith("git:"):
            source_commits_idx.append(i)

    if not source_commits_idx:
        print("  ERROR: Could not find '2014.03.15' commits")
        return

    # The source diff spans from (first_idx - 1) state to (last_idx) state.
    # Reconstruct older_store = state BEFORE first commit of this diff
    # Reconstruct newer_store = state AFTER last commit of this diff
    first_idx = min(source_commits_idx)
    last_idx = max(source_commits_idx)

    print(f"  Diff spans commits {first_idx} to {last_idx}")
    print(f"  Replaying to build stores...")

    # Build state before first_idx (= state after commit first_idx-1)
    older_store = InMemoryStore()
    for cm in commits[:first_idx]:
        c = db.get_commit(cm.id)
        if c and c.delta_data:
            delta = Delta.from_data(c.delta_data)
            older_store.apply_delta(delta)

    # Build newer_store = state after last_idx
    newer_store = InMemoryStore()
    for cm in commits[: last_idx + 1]:
        c = db.get_commit(cm.id)
        if c and c.delta_data:
            delta = Delta.from_data(c.delta_data)
            newer_store.apply_delta(delta)

    # Check which targets are in which store
    print(
        f"\n  Target note in older_store: {older_store.find_one(id=TARGET_NOTE) is not None}"
    )
    print(
        f"  Target note in newer_store: {newer_store.find_one(id=TARGET_NOTE) is not None}"
    )

    for aid in TARGET_ARROWS[:3]:
        in_older = older_store.find_one(id=aid) is not None
        in_newer = newer_store.find_one(id=aid) is not None
        print(f"  Arrow {aid[:16]} older={in_older} newer={in_newer}")

    # Now run the splitter and find where targets end up
    print(f"\n  Running infer_deltas_between_stores...")
    sub_groups = infer_deltas_between_stores(older_store, newer_store)
    print(f"  Result: {len(sub_groups)} sub-groups")

    # Find targets in sub-groups
    print(f"\n  Searching for targets in sub-groups:")
    for gi, (ts_ms, sub_delta, report) in enumerate(sub_groups):
        found_here = []
        for ch in sub_delta.changes():
            if ch.entity_id in ALL_TARGETS:
                found_here.append((ch.entity_id, ch.type().name))

        if found_here:
            dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
            print(f"\n  Sub-group {gi} (day={dt.date()}, report={report[:60]}):")
            for eid, ctype in found_here:
                label = "NOTE" if eid == TARGET_NOTE else "ARROW"
                print(f"    {label} {eid[:20]} {ctype}")

    # Also trace WHY the note ended up where it did
    print("\n" + "=" * 70)
    print("STEP 4: Trace WHY the note deletion was assigned to its day")
    print("=" * 70)

    # Reproduce the classification manually
    older_by_id = {e.id: e for e in older_store.find()}
    newer_by_id = {e.id: e for e in newer_store.find()}

    # Check the note
    old_note = older_by_id.get(TARGET_NOTE)
    new_note = newer_by_id.get(TARGET_NOTE)
    print(f"\n  Note in older: {old_note is not None}")
    print(f"  Note in newer: {new_note is not None}")
    if old_note and not new_note:
        print(f"  → Note is a DELETE (untimed)")
        # Check spatial matching
        if isinstance(old_note, Note):
            rect = old_note.rect()
            cx = int(round(rect.center().x()))
            cy = int(round(rect.center().y()))
            print(f"  Note center: ({cx}, {cy})")
            print(f"  Note geometry: {old_note.geometry}")

            # Check what timed notes are near this position
            timed_near = []
            for eid, entity in newer_by_id.items():
                if isinstance(entity, Note) and eid not in older_by_id:
                    # This is a CREATE
                    r = entity.rect()
                    ecx = int(round(r.center().x()))
                    ecy = int(round(r.center().y()))
                    if abs(ecx - cx) < 50 and abs(ecy - cy) < 50:
                        ts = _entity_modified_dt(entity)
                        timed_near.append((eid, ecx, ecy, ts))

            for eid, entity in newer_by_id.items():
                if isinstance(entity, Note) and eid in older_by_id:
                    old_e = older_by_id[eid]
                    if dump_to_dict(old_e) != dump_to_dict(entity):
                        # This is an UPDATE
                        r = entity.rect()
                        ecx = int(round(r.center().x()))
                        ecy = int(round(r.center().y()))
                        if abs(ecx - cx) < 50 and abs(ecy - cy) < 50:
                            ts = _entity_modified_dt(entity)
                            timed_near.append((eid, ecx, ecy, ts))

            if timed_near:
                print(f"  Spatial matches (within 50px):")
                for eid, ecx, ecy, ts in timed_near:
                    print(f"    {eid[:20]} at ({ecx},{ecy}) modified={ts}")
            else:
                print(f"  No spatial matches → goes to max_timed_date")

    # Check the arrows
    print(f"\n  Arrow classification:")
    for aid in TARGET_ARROWS[:3]:
        old_a = older_by_id.get(aid)
        new_a = newer_by_id.get(aid)
        if old_a and not new_a:
            print(f"  Arrow {aid[:16]}: DELETE")
            if isinstance(old_a, Arrow):
                print(f"    tail_note_id={old_a.tail_note_id}")
                print(f"    head_note_id={old_a.head_note_id}")
                # Check if head note has a timed day
                head_note = newer_by_id.get(old_a.head_note_id)
                if head_note:
                    ts = _entity_modified_dt(head_note)
                    print(f"    head note in newer: YES, modified={ts}")
                else:
                    head_note_old = older_by_id.get(old_a.head_note_id)
                    if head_note_old:
                        ts = _entity_modified_dt(head_note_old)
                        print(f"    head note only in older, modified={ts}")
                    else:
                        print(f"    head note: NOT FOUND")
        elif old_a and new_a:
            print(f"  Arrow {aid[:16]}: exists in BOTH stores (not part of diff)")
        elif not old_a:
            print(f"  Arrow {aid[:16]}: NOT in older store")


def main():
    find_source_diff()
    trace_splitter_assignment()
    trace_splitter_internals()


if __name__ == "__main__":
    main()
