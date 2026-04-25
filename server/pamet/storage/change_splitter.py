"""Infer fine-grained temporal deltas between two store states.

When the backward pipeline diffs consecutive git snapshots, the resulting
change set can span months (especially for Borg v4 snapshots).  This module
compares two ``InMemoryStore`` instances (older and newer), classifies each
entity difference using proper entity methods (``isinstance``,
``datetime_modified``, ``tail_note_id``, etc.), and groups them by day.

Arrows have no timestamps — they're assigned to the temporal group of
their connected notes via a piggyback heuristic.

Deletions have no reliable "deletion time" (the entity's ``modified``
reflects its last edit, not its removal), so they're placed in the
newest-timed-change group as fallback.

Usage in the backward pipeline
------------------------------
Instead of recording one commit per git-snapshot diff, call
``infer_deltas_between_stores()`` and record one commit per returned group.
The groups are returned newest→oldest (matching backward-walk order).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timezone

from fusion.libs.model import Entity, dump_to_dict
from fusion.storage.change import Change
from fusion.storage.delta import Delta
from fusion.storage.in_memory_store import InMemoryStore

from pamet.model.arrow import Arrow
from pamet.model.note import Note
from pamet.model.page import Page


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _entity_modified_dt(entity: Entity) -> datetime | None:
    """Extract datetime_modified from a Note or Page. Returns None for Arrow."""
    if isinstance(entity, (Note, Page)):
        try:
            return entity.datetime_modified
        except Exception:
            return None
    return None


MIN_CHANGES_TO_SPLIT = 3


def infer_deltas_between_stores(
    older_store: InMemoryStore,
    newer_store: InMemoryStore,
    *,
    min_changes: int = MIN_CHANGES_TO_SPLIT,
) -> list[tuple[float, Delta, str]]:
    """Compare two stores and produce day-grouped deltas.

    Parameters
    ----------
    older_store, newer_store
        Full entity stores representing the two snapshot states.
    min_changes
        Don't bother splitting if fewer total changes.

    Returns
    -------
    list of (timestamp_ms, sub_delta, report_str)
        Ordered **newest → oldest** (for backward-walk appending).
    """
    # ------------------------------------------------------------------
    # 1. Diff the two stores → classify each change
    # ------------------------------------------------------------------
    older_by_id = {e.id: e for e in older_store.find()}
    newer_by_id = {e.id: e for e in newer_store.find()}

    # (datetime | None, Change, Entity)
    timed: list[tuple[datetime, Change, Entity]] = []
    arrows: list[tuple[Change, Arrow]] = []
    untimed: list[Change] = []  # deletions, broken timestamps

    all_ids = set(older_by_id) | set(newer_by_id)

    for eid in all_ids:
        old_e = older_by_id.get(eid)
        new_e = newer_by_id.get(eid)

        if old_e is None:
            # CREATE
            change = Change.create(new_e)
            if isinstance(new_e, Arrow):
                arrows.append((change, new_e))
            else:
                ts = _entity_modified_dt(new_e)
                if ts:
                    timed.append((ts, change, new_e))
                else:
                    untimed.append(change)

        elif new_e is None:
            # DELETE — no reliable deletion timestamp
            change = Change.delete(old_e)
            if isinstance(old_e, Arrow):
                arrows.append((change, old_e))
            else:
                untimed.append(change)

        else:
            # Possible UPDATE
            if dump_to_dict(old_e) != dump_to_dict(new_e):
                change = Change.update(old_e, new_e)
                if isinstance(new_e, Arrow):
                    arrows.append((change, new_e))
                else:
                    ts = _entity_modified_dt(new_e)
                    if ts:
                        timed.append((ts, change, new_e))
                    else:
                        untimed.append(change)

    n_total = len(timed) + len(arrows) + len(untimed)

    if n_total == 0:
        return []

    # Fast path: small diff → single group
    if n_total < min_changes or not timed:
        all_changes = [ch for _, ch, _ in timed] + [ch for ch, _ in arrows] + untimed
        delta = Delta.from_changes(all_changes)
        # Use max timed ts or epoch as timestamp
        if timed:
            ts_ms = max(ts for ts, _, _ in timed).timestamp() * 1000
        else:
            ts_ms = 0
        return [(ts_ms, delta, f"no-split ({n_total}ch, {len(timed)} timed)")]

    # ------------------------------------------------------------------
    # 2. Group timed changes by calendar day
    # ------------------------------------------------------------------
    day_groups: dict[date, list[Change]] = defaultdict(list)
    for ts, ch, _ in timed:
        day_groups[ts.date()].append(ch)

    # Fallback day: newest entity timestamp in this diff
    max_timed_date = max(ts.date() for ts, _, _ in timed)

    # ------------------------------------------------------------------
    # 3. Arrow piggyback: link to connected notes' day
    # ------------------------------------------------------------------
    note_day: dict[str, date] = {}
    for ts, _, entity in timed:
        if isinstance(entity, Note):
            note_day[entity.id] = ts.date()

    arrows_linked = 0
    arrows_fallback = 0

    for ch, arrow in arrows:
        day = note_day.get(arrow.tail_note_id) if arrow.tail_note_id else None
        if day is None and arrow.head_note_id:
            day = note_day.get(arrow.head_note_id)
        if day is not None:
            day_groups[day].append(ch)
            arrows_linked += 1
        else:
            day_groups[max_timed_date].append(ch)
            arrows_fallback += 1

    # ------------------------------------------------------------------
    # 4. Untimed → newest timed day
    # ------------------------------------------------------------------
    if untimed:
        day_groups[max_timed_date].extend(untimed)

    # ------------------------------------------------------------------
    # 4b. Coalesce page creates/deletes with ALL their children.
    #
    # A page CREATE/DELETE must live in the same sub-group as every child
    # that is also created/deleted; otherwise reversing the sub-deltas
    # produces a page delete with dangling children (or a child create
    # before its parent page exists).
    # ------------------------------------------------------------------
    # Build change→day index and page_id→day for page-level changes
    change_day: dict[str, date] = {}  # entity_id → day
    page_change_day: dict[str, date] = (
        {}
    )  # page_id → day (for page-level CREATEs/DELETEs)
    for day, group in day_groups.items():
        for ch in group:
            change_day[ch.entity_id] = day
            # Page entities have no '-' in their id
            if "-" not in ch.entity_id:
                page_change_day[ch.entity_id] = day

    # Move children to their page's day if they're split
    moves: list[tuple[str, date, date]] = []  # (entity_id, from_day, to_day)
    for day, group in day_groups.items():
        for ch in group:
            if "-" in ch.entity_id:
                parent_id = ch.entity_id.split("-", 1)[0]
                if parent_id in page_change_day:
                    target_day = page_change_day[parent_id]
                    if day != target_day:
                        moves.append((ch.entity_id, day, target_day))

    for eid, from_day, to_day in moves:
        # Find and move the change object
        grp = day_groups[from_day]
        for i, ch in enumerate(grp):
            if ch.entity_id == eid:
                day_groups[to_day].append(grp.pop(i))
                break

    # Remove empty groups
    day_groups = {d: g for d, g in day_groups.items() if g}

    # ------------------------------------------------------------------
    # 5. Single group? No point splitting
    # ------------------------------------------------------------------
    if len(day_groups) <= 1:
        day = next(iter(day_groups))
        all_changes = [ch for _, ch, _ in timed] + [ch for ch, _ in arrows] + untimed
        delta = Delta.from_changes(all_changes)
        ts_ms = max(ts for ts, _, _ in timed).timestamp() * 1000
        return [(ts_ms, delta, f"no-split (all on {day}, {n_total} changes)")]

    # ------------------------------------------------------------------
    # 6. Build sub-deltas, newest day first
    # ------------------------------------------------------------------
    sorted_days = sorted(day_groups, reverse=True)
    result: list[tuple[float, Delta, str]] = []
    parts: list[str] = []
    arrow_eids = {ch.entity_id for ch, _ in arrows}

    for day in sorted_days:
        group = day_groups[day]
        sub_delta = Delta.from_changes(group)
        day_dt = datetime.combine(day, time(12, 0), tzinfo=timezone.utc)
        ts_ms = day_dt.timestamp() * 1000

        n_arrows_g = sum(1 for c in group if c.entity_id in arrow_eids)
        n_other = len(group) - n_arrows_g

        part = f"{day}:{len(group)}ch({n_other}NP {n_arrows_g}A)"
        parts.append(part)
        result.append((ts_ms, sub_delta, part))

    summary = (
        f"SPLIT {n_total}ch → {len(sorted_days)} groups  "
        f'[{", ".join(parts)}]  '
        f"arrows: {arrows_linked} linked, {arrows_fallback} fallback  "
        f"untimed: {len(untimed)}"
    )
    # Attach full summary to first element
    result[0] = (result[0][0], result[0][1], summary)

    return result
