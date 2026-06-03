"""CLI commands for exploring VCS history and diagnosing migration issues.

These commands operate on the change-history.db SQLite database, seeking
to specific commits and running diagnostics on the store state at that point.
"""

from __future__ import annotations

import builtins
import sys
from pathlib import Path

import click

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sivkit.libs.model import load_from_dict
from sivkit.storage.commit import Commit
from sivkit.storage.delta import Delta
from sivkit.storage.in_memory_store import InMemoryStore
from sivkit.storage.sqlite_vcs_adapter import SqliteVcsAdapter

from pamet.model.arrow import Arrow  # noqa: F401 — register entity type
from pamet.model.card_note import CardNote  # noqa: F401
from pamet.model.note import Note
from pamet.model.page import Page  # noqa: F401
from pamet.model.script_note import ScriptNote  # noqa: F401
from pamet.storage.pamet_in_memory_store import PametInMemoryStore

python_list = builtins.list


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def open_adapter(repo: Path) -> SqliteVcsAdapter:
    """Open the VCS SQLite adapter for a pamet repo."""
    db_path = repo / ".pamet" / "change-history.db"
    if not db_path.exists():
        raise click.ClickException(f"No history DB at {db_path}")
    return SqliteVcsAdapter(db_path)


def get_branch_chain(adapter: SqliteVcsAdapter, branch: str = "main") -> list[str]:
    """Get the full commit chain for a branch (oldest first)."""
    graph = adapter.get_commit_graph()
    br = graph.branch(branch)
    if br is None or br.head_commit_id is None:
        raise click.ClickException(f"Branch '{branch}' not found or empty")
    # walk_chain returns [head, parent, ..., root]
    chain = adapter.walk_chain(br.head_commit_id)
    chain.reverse()  # now oldest first
    return chain


def resolve_commit_ref(chain: list[str], ref: str) -> tuple[int, str]:
    """Resolve a commit reference to (index, commit_id).

    ref can be:
      - A commit ID (or prefix)
      - A positive integer index (0 = oldest)
      - A negative integer (-1 = head, -100 = 100 back from head)
    """
    # Try as integer index
    try:
        idx = int(ref)
        if idx < 0:
            idx = len(chain) + idx
        if idx < 0 or idx >= len(chain):
            raise click.ClickException(f"Index {ref} out of range (0..{len(chain)-1})")
        return idx, chain[idx]
    except ValueError:
        pass

    # Try as commit ID prefix
    matches = [cid for cid in chain if cid.startswith(ref)]
    if len(matches) == 1:
        idx = chain.index(matches[0])
        return idx, matches[0]
    elif len(matches) > 1:
        raise click.ClickException(
            f"Ambiguous commit prefix '{ref}' — matches {len(matches)} commits"
        )
    else:
        raise click.ClickException(f"Commit '{ref}' not found")


def seek_to_commit(
    adapter: SqliteVcsAdapter,
    chain: list[str],
    target_idx: int,
    use_snapshots: bool = False,
) -> PametInMemoryStore:
    """Load the store state at a specific commit index.

    If use_snapshots=True, finds the nearest snapshot and replays from there.
    Otherwise replays all deltas from the beginning (slower but always correct).
    """
    target_id = chain[target_idx]
    store = PametInMemoryStore()
    start_idx = 0

    if use_snapshots:
        # Find nearest snapshot at or before target
        backward_from_target = adapter.walk_chain(target_id)
        for cid in backward_from_target:
            if adapter.has_snapshot(cid):
                snapshot_data = adapter.load_snapshot(cid)
                if snapshot_data:
                    for entity_id, entity_dict in snapshot_data.items():
                        entity = load_from_dict(entity_dict)
                        store.insert_one(entity)
                    start_idx = chain.index(cid) + 1
                break

    # Replay deltas from start to target (inclusive)
    ids_to_replay = chain[start_idx : target_idx + 1]
    if ids_to_replay:
        CHUNK = 500
        for chunk_start in range(0, len(ids_to_replay), CHUNK):
            chunk_ids = ids_to_replay[chunk_start : chunk_start + CHUNK]
            commits = adapter.get_commits(chunk_ids)
            for commit in commits:
                delta = Delta.from_data(commit.delta_data)
                store.apply_delta(delta)

    return store


def find_page_in_store(store: PametInMemoryStore, name: str) -> Page | None:
    """Find a page by name (case-insensitive)."""
    for page in store.pages():
        if page.name.lower() == name.lower():
            return page
    return None


def note_text_short(note: Note) -> str:
    """Short text preview of a note."""
    c = note.content
    parts = []
    if c.get("text"):
        parts.append(c["text"])
    if c.get("url"):
        parts.append(f"[url: {c['url']}]")
    if c.get("page_ref"):
        ref = c["page_ref"]
        parts.append(f"[→ {ref.get('path', ref.get('id', '?'))}]")
    text = " ".join(parts) if parts else "[empty]"
    first_line = text.split("\n")[0]
    return first_line[:80]


def format_timestamp(ts_ms: float) -> str:
    """Format millisecond timestamp to readable date."""
    from datetime import datetime, timezone

    dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M")


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------


@click.group(epilog="""
\b
COMMIT REFERENCES:
  Commands accept commit references as:
    - Positive index: 0 = oldest commit, 1000 = 1001st commit
    - Negative index: -1 = HEAD (newest), -100 = 100 back from head
    - Commit ID or prefix: e.g. "abc123"
\b
SEEKING:
  The tool finds the nearest snapshot and replays deltas forward.
  First seek may be slow; subsequent seeks near the same area are faster.
""")
@click.option(
    "--repo",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    envvar="PAMET_REPO",
    required=True,
    help="Path to Pamet repository (or set PAMET_REPO env var).",
)
@click.pass_context
def history(ctx: click.Context, repo: Path) -> None:
    """Explore VCS history and diagnose migration issues."""
    ctx.ensure_object(dict)
    ctx.obj["repo"] = repo
    ctx.obj["adapter"] = open_adapter(repo)


# ---------------------------------------------------------------------------
# info
# ---------------------------------------------------------------------------


@history.command()
@click.pass_context
def info(ctx: click.Context) -> None:
    """Show VCS stats: total commits, branches, snapshots, time range."""
    adapter: SqliteVcsAdapter = ctx.obj["adapter"]
    graph = adapter.get_commit_graph()
    branches = graph.branches()

    click.echo(f"Repository: {ctx.obj['repo']}")
    click.echo(f"Branches: {len(branches)}")

    for br in branches:
        click.echo(f"\n  Branch '{br.name}':")
        if br.head_commit_id is None:
            click.echo("    (empty)")
            continue

        chain = adapter.walk_chain(br.head_commit_id)
        click.echo(f"    Commits: {len(chain)}")

        # Time range from first and last commit
        root_commit = adapter.get_commit(chain[-1])
        head_commit = adapter.get_commit(chain[0])
        if root_commit and head_commit:
            click.echo(f"    Oldest: {format_timestamp(root_commit.timestamp)}")
            click.echo(f"    Newest: {format_timestamp(head_commit.timestamp)}")

    snap_ids = adapter.snapshot_commit_ids()
    click.echo(f"\n  Snapshots stored: {len(snap_ids)}")


# ---------------------------------------------------------------------------
# seek
# ---------------------------------------------------------------------------


@history.command()
@click.argument("ref")
@click.pass_context
def seek(ctx: click.Context, ref: str) -> None:
    """Load store state at a commit and print summary.

    REF is a commit index (0=oldest, -1=head) or commit ID prefix.
    """
    adapter: SqliteVcsAdapter = ctx.obj["adapter"]
    chain = get_branch_chain(adapter)
    idx, commit_id = resolve_commit_ref(chain, ref)

    commit = adapter.get_commit(commit_id)
    click.echo(
        f"Seeking to commit {idx}/{len(chain)-1} "
        f"(id={commit_id[:12]}..., {format_timestamp(commit.timestamp)}, "
        f"msg={commit.message[:60]!r})"
    )

    store = seek_to_commit(adapter, chain, idx)

    pages = python_list(store.pages())
    total_notes = sum(1 for p in pages for _ in store.notes(p.id))
    total_arrows = sum(1 for p in pages for _ in store.arrows(p.id))

    click.echo(
        f"\nStore state: {len(pages)} pages, {total_notes} notes, {total_arrows} arrows"
    )
    click.echo("\nPages:")
    for page in sorted(pages, key=lambda p: p.name):
        n = sum(1 for _ in store.notes(page.id))
        a = sum(1 for _ in store.arrows(page.id))
        click.echo(f"  {page.name}  ({n} notes, {a} arrows)")


# ---------------------------------------------------------------------------
# bad-arrows
# ---------------------------------------------------------------------------


@history.command("bad-arrows")
@click.argument("ref")
@click.option("--page", required=True, help="Page name to check.")
@click.option("--verbose", "-v", is_flag=True, help="Show full arrow/note details.")
@click.pass_context
def bad_arrows(ctx: click.Context, ref: str, page: str, verbose: bool) -> None:
    """Find arrows with broken anchors at a specific commit.

    Reports arrows whose head or tail note_anchor_id references a note
    that doesn't exist on the page at that point in history.
    """
    adapter: SqliteVcsAdapter = ctx.obj["adapter"]
    chain = get_branch_chain(adapter)
    idx, commit_id = resolve_commit_ref(chain, ref)

    commit = adapter.get_commit(commit_id)
    click.echo(
        f"Commit {idx}/{len(chain)-1}: {format_timestamp(commit.timestamp)} "
        f"msg={commit.message[:60]!r}"
    )
    click.echo("Seeking...")

    store = seek_to_commit(adapter, chain, idx)

    pg = find_page_in_store(store, page)
    if not pg:
        click.echo(f"Page '{page}' not found at this commit.")
        click.echo("Available pages:")
        for p in sorted(store.pages(), key=lambda p: p.name):
            click.echo(f"  {p.name}")
        return

    notes_on_page = {n.id: n for n in store.notes(pg.id)}
    bad = []

    for arrow in store.arrows(pg.id):
        tail_id = arrow.tail.get("note_anchor_id")
        head_id = arrow.head.get("note_anchor_id")

        bad_tail = bool(tail_id and tail_id not in notes_on_page)
        bad_head = bool(head_id and head_id not in notes_on_page)

        if bad_tail or bad_head:
            bad.append((arrow, bad_tail, bad_head, tail_id, head_id))

    click.echo(
        f"\nPage '{pg.name}': {len(notes_on_page)} notes, "
        f"{sum(1 for _ in store.arrows(pg.id))} arrows, "
        f"{len(bad)} bad arrows"
    )

    if not bad:
        click.echo("  No broken arrows found.")
        return

    for arrow, bad_tail, bad_head, tail_id, head_id in bad:
        parts = []
        if bad_tail:
            parts.append(f"tail→MISSING({tail_id})")
        if bad_head:
            parts.append(f"head→MISSING({head_id})")
        label = ", ".join(parts)

        # Context from the valid end
        context_parts = []
        if not bad_tail and tail_id and tail_id in notes_on_page:
            context_parts.append(f"tail: {note_text_short(notes_on_page[tail_id])}")
        if not bad_head and head_id and head_id in notes_on_page:
            context_parts.append(f"head: {note_text_short(notes_on_page[head_id])}")

        if verbose:
            click.echo(f"\n  arrow_id={arrow.id}")
            click.echo(f"    {label}")
            if context_parts:
                for cp in context_parts:
                    click.echo(f"    {cp}")
        else:
            ctx_str = f"  ({'; '.join(context_parts)})" if context_parts else ""
            click.echo(f"  {label}{ctx_str}")


# ---------------------------------------------------------------------------
# overlapping-notes
# ---------------------------------------------------------------------------


@history.command("overlapping-notes")
@click.argument("ref")
@click.option("--page", required=True, help="Page name to check.")
@click.option(
    "--min-overlap",
    type=float,
    default=0.5,
    help="Minimum overlap ratio (intersection / smaller note area). Default 0.5.",
)
@click.option("--verbose", "-v", is_flag=True, help="Show note IDs and geometry.")
@click.pass_context
def overlapping_notes(
    ctx: click.Context, ref: str, page: str, min_overlap: float, verbose: bool
) -> None:
    """Find overlapping notes at a specific commit.

    Reports pairs of notes whose bounding rectangles overlap by at least
    --min-overlap ratio relative to the smaller note.
    """
    adapter: SqliteVcsAdapter = ctx.obj["adapter"]
    chain = get_branch_chain(adapter)
    idx, commit_id = resolve_commit_ref(chain, ref)

    commit = adapter.get_commit(commit_id)
    click.echo(
        f"Commit {idx}/{len(chain)-1}: {format_timestamp(commit.timestamp)} "
        f"msg={commit.message[:60]!r}"
    )
    click.echo("Seeking...")

    store = seek_to_commit(adapter, chain, idx)

    pg = find_page_in_store(store, page)
    if not pg:
        click.echo(f"Page '{page}' not found at this commit.")
        return

    all_notes = python_list(store.notes(pg.id))
    overlaps = []

    for i in range(len(all_notes)):
        rect_i = all_notes[i].rect()
        for j in range(i + 1, len(all_notes)):
            rect_j = all_notes[j].rect()
            intersection = rect_i.intersection(rect_j)
            if intersection is None:
                continue

            inter_area = intersection.width() * intersection.height()
            smaller_area = min(
                rect_i.width() * rect_i.height(),
                rect_j.width() * rect_j.height(),
            )
            if smaller_area <= 0:
                continue

            ratio = inter_area / smaller_area
            if ratio >= min_overlap:
                overlaps.append((all_notes[i], all_notes[j], ratio))

    click.echo(
        f"\nPage '{pg.name}': {len(all_notes)} notes, {len(overlaps)} overlapping pairs"
    )

    if not overlaps:
        click.echo("  No significant overlaps found.")
        return

    overlaps.sort(key=lambda x: x[2], reverse=True)

    for note_a, note_b, ratio in overlaps:
        ca = note_a.rect().center()
        cb = note_b.rect().center()
        text_a = note_text_short(note_a)
        text_b = note_text_short(note_b)

        if verbose:
            click.echo(f"\n  [{ratio:.0%} overlap]")
            click.echo(
                f"    A: id={note_a.id} ({ca.x():+.0f},{ca.y():+.0f}) "
                f"{note_a.width:.0f}x{note_a.height:.0f}  {text_a}"
            )
            click.echo(
                f"    B: id={note_b.id} ({cb.x():+.0f},{cb.y():+.0f}) "
                f"{note_b.width:.0f}x{note_b.height:.0f}  {text_b}"
            )
        else:
            click.echo(
                f'  [{ratio:.0%}] ({ca.x():+.0f},{ca.y():+.0f}) "{text_a}" ∩ '
                f'({cb.x():+.0f},{cb.y():+.0f}) "{text_b}"'
            )


# ---------------------------------------------------------------------------
# scan-range
# ---------------------------------------------------------------------------


@history.command("scan-range")
@click.option("--start", required=True, help="Start commit ref (index or ID).")
@click.option("--end", required=True, help="End commit ref (index or ID).")
@click.option("--step", type=int, default=1, help="Check every Nth commit. Default 1.")
@click.option("--page", required=True, help="Page name to check.")
@click.option(
    "--check",
    type=click.Choice(["arrows", "overlaps", "both"]),
    default="both",
    help="What to check. Default: both.",
)
@click.option(
    "--min-overlap",
    type=float,
    default=0.5,
    help="Overlap threshold for overlap checks.",
)
@click.pass_context
def scan_range(
    ctx: click.Context,
    start: str,
    end: str,
    step: int,
    page: str,
    check: str,
    min_overlap: float,
) -> None:
    """Scan a range of commits for bad arrows and/or overlapping notes.

    Outputs a summary showing which commits have issues, so you can
    identify when problems first appear.
    """
    adapter: SqliteVcsAdapter = ctx.obj["adapter"]
    chain = get_branch_chain(adapter)
    start_idx, _ = resolve_commit_ref(chain, start)
    end_idx, _ = resolve_commit_ref(chain, end)

    if start_idx > end_idx:
        start_idx, end_idx = end_idx, start_idx

    click.echo(
        f"Scanning commits {start_idx}..{end_idx} (step={step}) "
        f"page='{page}' check={check}"
    )
    click.echo(
        f"{'idx':>6} {'date':>16} {'notes':>6} {'arrows':>7} "
        f"{'bad_arr':>8} {'overlaps':>9}"
    )
    click.echo("-" * 70)

    for i in range(start_idx, end_idx + 1, step):
        store = seek_to_commit(adapter, chain, i)
        pg = find_page_in_store(store, page)

        if not pg:
            click.echo(f"{i:>6}  — page not found —")
            continue

        commit = adapter.get_commit(chain[i])
        date_str = format_timestamp(commit.timestamp) if commit else "?"

        notes_on_page = {n.id: n for n in store.notes(pg.id)}
        n_notes = len(notes_on_page)
        n_arrows = sum(1 for _ in store.arrows(pg.id))

        bad_count = 0
        overlap_count = 0

        if check in ("arrows", "both"):
            for arrow in store.arrows(pg.id):
                tail_id = arrow.tail.get("note_anchor_id")
                head_id = arrow.head.get("note_anchor_id")
                if (tail_id and tail_id not in notes_on_page) or (
                    head_id and head_id not in notes_on_page
                ):
                    bad_count += 1

        if check in ("overlaps", "both"):
            all_notes = python_list(notes_on_page.values())
            for i2 in range(len(all_notes)):
                rect_i = all_notes[i2].rect()
                for j2 in range(i2 + 1, len(all_notes)):
                    rect_j = all_notes[j2].rect()
                    intersection = rect_i.intersection(rect_j)
                    if intersection is None:
                        continue
                    inter_area = intersection.width() * intersection.height()
                    smaller_area = min(
                        rect_i.width() * rect_i.height(),
                        rect_j.width() * rect_j.height(),
                    )
                    if smaller_area > 0 and inter_area / smaller_area >= min_overlap:
                        overlap_count += 1

        marker = ""
        if bad_count or overlap_count:
            marker = " ←"

        click.echo(
            f"{i:>6} {date_str:>16} {n_notes:>6} {n_arrows:>7} "
            f"{bad_count:>8} {overlap_count:>9}{marker}"
        )


# ---------------------------------------------------------------------------
# commits (list commits touching a page)
# ---------------------------------------------------------------------------


@history.command("commits")
@click.option("--page", required=True, help="Page name to filter by.")
@click.option("--around", default=None, help="Show commits around this ref.")
@click.option("-n", "--count", type=int, default=20, help="Number of commits to show.")
@click.pass_context
def commits_cmd(ctx: click.Context, page: str, around: str | None, count: int) -> None:
    """List commits that touch a specific page.

    Checks delta_data for entity IDs containing the page's ID prefix.
    Use --around to center the listing around a specific commit.
    """
    adapter: SqliteVcsAdapter = ctx.obj["adapter"]
    chain = get_branch_chain(adapter)

    # First, find the page ID by seeking to head
    click.echo("Loading head state to find page ID...")
    store = seek_to_commit(adapter, chain, len(chain) - 1)
    pg = find_page_in_store(store, page)
    if not pg:
        click.echo(f"Page '{page}' not found at HEAD. Try seeking to find it.")
        return

    page_id = pg.id
    click.echo(f"Page '{page}' id={page_id}")

    # Determine range to scan
    if around:
        center_idx, _ = resolve_commit_ref(chain, around)
    else:
        center_idx = len(chain) - 1  # default to head

    start_idx = max(0, center_idx - count // 2)
    end_idx = min(len(chain), start_idx + count)

    # Fetch commits in range and check deltas
    ids_in_range = chain[start_idx:end_idx]
    fetched = adapter.get_commits(ids_in_range)

    click.echo(f"\nCommits {start_idx}..{end_idx - 1} touching page '{page}':\n")
    click.echo(f"{'idx':>6} {'date':>16} {'changes':>8} {'msg'}")
    click.echo("-" * 70)

    for offset, commit in enumerate(fetched):
        # Check if any entity ID in the delta starts with page_id
        touching = [
            eid
            for eid in commit.delta_data.keys()
            if eid == page_id or eid.startswith(page_id + "-")
        ]
        if touching:
            idx = start_idx + offset
            date_str = format_timestamp(commit.timestamp)
            click.echo(
                f"{idx:>6} {date_str:>16} {len(touching):>8} " f"{commit.message[:40]}"
            )


# ---------------------------------------------------------------------------
# Snapshot management
# ---------------------------------------------------------------------------


@history.command("list-snapshots")
@click.pass_context
def list_snapshots(ctx: click.Context) -> None:
    """List all stored snapshots with their commit index and date."""
    adapter: SqliteVcsAdapter = ctx.obj["adapter"]
    chain = get_branch_chain(adapter)
    snap_ids = set(adapter.snapshot_commit_ids())

    if not snap_ids:
        click.echo("No snapshots stored.")
        return

    click.echo(f"{len(snap_ids)} snapshots:\n")
    click.echo(f"{'idx':>6} {'date':>16} {'commit_id'}")
    click.echo("-" * 50)

    for i, cid in enumerate(chain):
        if cid in snap_ids:
            commit = adapter.get_commit(cid)
            date_str = format_timestamp(commit.timestamp) if commit else "?"
            click.echo(f"{i:>6} {date_str:>16} {cid[:16]}")


@history.command("save-snapshot")
@click.argument("ref")
@click.pass_context
def save_snapshot(ctx: click.Context, ref: str) -> None:
    """Save a snapshot at a specific commit (seeks and stores the full state)."""
    from sivkit.libs.model import dump_to_dict

    adapter: SqliteVcsAdapter = ctx.obj["adapter"]
    chain = get_branch_chain(adapter)
    idx, commit_id = resolve_commit_ref(chain, ref)

    if adapter.has_snapshot(commit_id):
        click.echo(f"Snapshot already exists at commit {idx} ({commit_id[:12]})")
        return

    click.echo(f"Seeking to commit {idx}...")
    store = seek_to_commit(adapter, chain, idx)

    snap = {e.id: dump_to_dict(e) for e in store.find()}
    adapter.save_snapshot(commit_id, snap)
    click.echo(f"Saved snapshot at commit {idx} ({len(snap)} entities).")


@history.command("remove-snapshot")
@click.argument("ref")
@click.pass_context
def remove_snapshot(ctx: click.Context, ref: str) -> None:
    """Remove a snapshot at a specific commit."""
    import peewee as pw
    from sivkit.storage.sqlite_vcs_adapter import SnapshotRow

    adapter: SqliteVcsAdapter = ctx.obj["adapter"]
    chain = get_branch_chain(adapter)
    idx, commit_id = resolve_commit_ref(chain, ref)

    if not adapter.has_snapshot(commit_id):
        click.echo(f"No snapshot at commit {idx} ({commit_id[:12]})")
        return

    db = pw.SqliteDatabase(
        str(ctx.obj["repo"] / ".pamet" / "change-history.db"),
        pragmas={"journal_mode": "wal"},
    )
    with db.bind_ctx([SnapshotRow]):
        SnapshotRow.delete().where(SnapshotRow.commit_id == commit_id).execute()

    click.echo(f"Removed snapshot at commit {idx} ({commit_id[:12]}).")


@history.command("trace-entity")
@click.argument("entity_id")
@click.option("--start", default="0", help="Start commit ref (default: 0)")
@click.option("--end", default="-1", help="End commit ref (default: -1 = HEAD)")
@click.pass_context
def trace_entity(ctx: click.Context, entity_id: str, start: str, end: str) -> None:
    """Trace all changes to an entity across commit history.

    Shows every commit where the entity is created, updated, or deleted,
    along with the commit message and timestamp. Useful for understanding
    when and why an entity appears/disappears.
    """
    from datetime import datetime

    adapter: SqliteVcsAdapter = ctx.obj["adapter"]
    chain = get_branch_chain(adapter)
    start_idx, _ = resolve_commit_ref(chain, start)
    end_idx, _ = resolve_commit_ref(chain, end)

    click.echo(f"Tracing entity {entity_id} in commits {start_idx}..{end_idx}")
    click.echo("-" * 70)

    found = 0
    for i in range(start_idx, end_idx + 1):
        commit_id = chain[i]
        commit = adapter.get_commit(commit_id)
        if not commit or not commit.delta_data:
            continue

        delta = Delta.from_data(commit.delta_data)
        for ch in delta.changes():
            if ch.entity_id == entity_id:
                dt = datetime.fromtimestamp(commit.timestamp / 1000)
                ctype = ch.type().name
                click.echo(
                    f"  commit {i:>6} [{dt.strftime('%Y-%m-%d %H:%M')}] "
                    f"{ctype:8s} {commit.message[:60]}"
                )
                found += 1

    if not found:
        click.echo(f"  (no changes found for {entity_id})")
    else:
        click.echo(f"\n  {found} change(s) found.")


if __name__ == "__main__":
    history()
