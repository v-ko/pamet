#!/usr/bin/env python3
"""CLI for exploring Pamet notes spatially.

Set PAMET_REPO to avoid passing --repo every time:
    export PAMET_REPO=/sync/pamet/repo

Usage:
    pamet-notes list
    pamet-notes overview <page_name> [-r RADIUS] [--cx X] [--cy Y]
    pamet-notes area <page_name> --cx X --cy Y -r RADIUS
    pamet-notes search <query> [--page <page_name>]
"""

from __future__ import annotations

import builtins
import sys
from pathlib import Path

import click

# Add the server package to the path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fusion.util import Point2D

from pamet.desktop_app.config import get_repo_settings
from pamet.model.arrow import Arrow
from pamet.model.note import Note
from pamet.model.page import Page
from pamet.storage.pamet_in_memory_store import PametInMemoryStore
from pamet.storage.project_walk import iter_canvas_paths
from pamet.storage.service_utils import (
    CanvasParseError,
    ForeignCanvasFile,
    read_canvas_file,
)

# Alias to avoid shadowing builtin list
python_list = builtins.list


def load_store(repo_path: Path) -> PametInMemoryStore:
    """Load all canvas files into a bare PametInMemoryStore (read-only)."""
    store = PametInMemoryStore()
    repo = repo_path.resolve()
    settings = get_repo_settings(repo)
    exclude_patterns = [
        pat for pat, enabled in settings.get("files.exclude", {}).items() if enabled
    ]
    for canvas_path in iter_canvas_paths(repo, exclude_patterns):
        try:
            entities = read_canvas_file(canvas_path, repo)
        except (ForeignCanvasFile, CanvasParseError):
            continue
        for entity in entities.values():
            store.insert_one(entity)
    return store


def find_page(store: PametInMemoryStore, name: str) -> Page | None:
    """Find a page by name (case-insensitive)."""
    for page in store.pages():
        if page.name.lower() == name.lower():
            return page
    return None


def note_text(note: Note) -> str:
    """Readable text representation of a note's content."""
    c = note.content
    parts = []
    if c.get("text"):
        parts.append(c["text"])
    if c.get("url"):
        parts.append(f"[url: {c['url']}]")
    if c.get("page_ref"):
        ref = c["page_ref"]
        parts.append(f"[→ {ref.get('path', ref.get('id', '?'))}]")
    if c.get("image"):
        parts.append(f"[image: {c['image'].get('path', '?')}]")
    return " ".join(parts) if parts else "[empty]"


def note_dist(note: Note, cx: float, cy: float) -> float:
    """Distance from note center to a point."""
    return note.rect().center().distance_to(Point2D(cx, cy))


def notes_in_radius(
    store: PametInMemoryStore, page: Page, cx: float, cy: float, radius: float
) -> list[Note]:
    """Return notes within radius of (cx, cy), sorted by distance."""
    target = Point2D(cx, cy)
    result = [
        n
        for n in store.notes(page.id)
        if n.rect().center().distance_to(target) <= radius
    ]
    result.sort(key=lambda n: n.rect().center().distance_to(target))
    return result


def resolve_arrows(
    store: PametInMemoryStore, page: Page
) -> list[tuple[Arrow, Note | None, Note | None]]:
    """Return arrows with their resolved tail/head notes."""
    notes_by_id = {n.id: n for n in store.notes(page.id)}
    result = []
    for arrow in store.arrows(page.id):
        tail_id = arrow.tail.get("note_anchor_id")
        head_id = arrow.head.get("note_anchor_id")
        tail_note = notes_by_id.get(tail_id) if tail_id else None
        head_note = notes_by_id.get(head_id) if head_id else None
        result.append((arrow, tail_note, head_note))
    return result


def format_note_compact(note: Note, cx: float = 0, cy: float = 0) -> str:
    center = note.rect().center()
    dist = note_dist(note, cx, cy)
    text = note_text(note)
    lines = text.split("\n")
    if len(lines) > 3:
        preview = "\n    ".join(lines[:3]) + f"\n    ... ({len(lines)} lines total)"
    else:
        preview = "\n    ".join(lines)
    return f"  ({center.x():+.0f}, {center.y():+.0f}) {note.width:.0f}x{note.height:.0f}  d={dist:.0f}  {preview}"


def format_arrow_text(note: Note | None) -> str:
    if note is None:
        return "[free point]"
    text = note_text(note)
    first_line = text.split("\n")[0]
    if len(first_line) > 60:
        first_line = first_line[:57] + "..."
    return first_line


pass_store = click.make_pass_decorator(PametInMemoryStore)


@click.group(epilog="""
\b
DATA MODEL:
  Notes are rectangles on an infinite 2D canvas (coordinates in pixels).
  Each note has: center position (x, y), width, height, and text content.
  Notes may also contain URLs, page references ([→ page.canvas]), or images.
  Arrows connect notes (shown as "tail → head" in output).
  Pages are separate canvases, each stored as a .canvas.html file.
\b
SPATIAL LAYOUT:
  The origin (0, 0) is typically the center of a page.
  Notes radiate outward: title/core ideas near center, details in periphery.
  Typical page radius: 500-2000 pixels. A note is usually 160-520px wide.
  Coordinates: +X is right, +Y is down.
\b
WORKFLOW (for LLM agents):
  1. 'list' to see all pages and pick one to explore.
  2. 'overview PAGE' to see the full page sorted by distance from center.
  3. 'overview PAGE -r 500' to zoom in on the central cluster.
  4. 'area PAGE --cx X --cy Y -r R' to read full text of a specific cluster.
  5. 'search QUERY' to find notes across all pages, then use the reported
     coordinates with 'overview' or 'area' to explore the surrounding context.
  Each note in the output shows: (center_x, center_y) WxH  d=DIST  text...
  'd' is the Euclidean distance from the query center to the note center.
""")
@click.option(
    "--repo",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    envvar="PAMET_REPO",
    required=True,
    help="Path to Pamet repository (or set PAMET_REPO env var).",
)
@click.pass_context
def cli(ctx: click.Context, repo: Path) -> None:
    """Explore a Pamet notes repository. Notes are spatially arranged on 2D
    canvas pages. Use spatial queries (center + radius) to navigate."""
    click.echo(f"Loading repo: {repo} ...", err=True)
    ctx.obj = load_store(repo)
    click.echo(f"Loaded {len(python_list(ctx.obj.pages()))} pages.\n", err=True)


@cli.command("list")
@pass_store
def list_pages(store: PametInMemoryStore) -> None:
    """List all pages with note/arrow counts. Use this first to find
    page names for other commands."""
    pages = sorted(store.pages(), key=lambda p: p.name)
    click.echo(f"{len(pages)} pages:\n")
    for page in pages:
        notes = sum(1 for _ in store.notes(page.id))
        arrows = sum(1 for _ in store.arrows(page.id))
        click.echo(f"  {page.name}  ({notes} notes, {arrows} arrows)")


@cli.command()
@click.argument("page")
@click.option(
    "--cx",
    type=float,
    default=0,
    help="Center X in canvas pixels (default: 0 = page center).",
)
@click.option(
    "--cy",
    type=float,
    default=0,
    help="Center Y in canvas pixels (default: 0 = page center).",
)
@click.option(
    "-r",
    "--radius",
    type=float,
    default=float("inf"),
    help="Only show notes whose center is within this radius (pixels). "
    "Omit to show all notes. Start with 500 for the core cluster.",
)
@pass_store
def overview(
    store: PametInMemoryStore, page: str, cx: float, cy: float, radius: float
) -> None:
    """Compact overview: each note shown as one line with position, size, distance,
    and truncated text (max 3 lines). Use to scan a page and find regions of
    interest, then drill in with 'area' for full text."""
    pg = find_page(store, page)
    if not pg:
        click.echo(f"Page '{page}' not found. Similar:")
        for p in sorted(store.pages(), key=lambda p: p.name):
            if page.lower() in p.name.lower():
                click.echo(f"  {p.name}")
        return

    all_notes = python_list(store.notes(pg.id))

    if radius < float("inf"):
        notes = notes_in_radius(store, pg, cx, cy, radius)
    else:
        notes = sorted(all_notes, key=lambda n: note_dist(n, cx, cy))

    if notes:
        all_x = [n.geometry[0] for n in notes] + [
            n.geometry[0] + n.geometry[2] for n in notes
        ]
        all_y = [n.geometry[1] for n in notes] + [
            n.geometry[1] + n.geometry[3] for n in notes
        ]
        extent = f"  extent: x[{min(all_x):.0f}..{max(all_x):.0f}] y[{min(all_y):.0f}..{max(all_y):.0f}]"
    else:
        extent = ""

    resolved = resolve_arrows(store, pg)

    click.echo(f"=== {pg.name} ===")
    click.echo(
        f"  {len(notes)}/{len(all_notes)} notes shown (center: {cx},{cy}  radius: {radius})"
    )
    click.echo(f"  {len(resolved)} arrows on page")
    if extent:
        click.echo(extent)
    click.echo()

    for note in notes:
        click.echo(format_note_compact(note, cx, cy))

    visible_ids = {n.id for n in notes}
    visible_arrows = [
        (a, t, h)
        for a, t, h in resolved
        if (t and t.id in visible_ids) or (h and h.id in visible_ids)
    ]
    if visible_arrows:
        click.echo(f"\n  Arrows ({len(visible_arrows)} involving visible notes):")
        for arrow, tail_note, head_note in visible_arrows:
            click.echo(
                f"    {format_arrow_text(tail_note)}  →  {format_arrow_text(head_note)}"
            )
    click.echo()


@cli.command()
@click.argument("page")
@click.option("--cx", type=float, required=True, help="Center X in canvas pixels.")
@click.option("--cy", type=float, required=True, help="Center Y in canvas pixels.")
@click.option(
    "-r",
    "--radius",
    type=float,
    required=True,
    help="Radius in pixels. 200-400 for a tight cluster, 800+ for a wide area.",
)
@pass_store
def area(
    store: PametInMemoryStore, page: str, cx: float, cy: float, radius: float
) -> None:
    """Full-text read of notes in a circular area. Unlike 'overview', text is
    not truncated — use this to read the actual content of notes you identified
    via 'overview' or 'search'. Pick cx/cy from the coordinates shown in those
    commands."""
    pg = find_page(store, page)
    if not pg:
        click.echo(f"Page '{page}' not found.")
        return

    notes = notes_in_radius(store, pg, cx, cy, radius)

    click.echo(
        f"=== {pg.name} — area cx={cx} cy={cy} r={radius} — {len(notes)} notes ===\n"
    )

    for note in notes:
        center = note.rect().center()
        dist = note_dist(note, cx, cy)
        text = note_text(note)
        click.echo(
            f"--- ({center.x():+.0f}, {center.y():+.0f}) {note.width:.0f}x{note.height:.0f}  d={dist:.0f} ---"
        )
        click.echo(text)
        click.echo()

    visible_ids = {n.id for n in notes}
    resolved = resolve_arrows(store, pg)
    local_arrows = [
        (a, t, h)
        for a, t, h in resolved
        if (t and t.id in visible_ids) or (h and h.id in visible_ids)
    ]
    if local_arrows:
        click.echo(f"Arrows ({len(local_arrows)}):")
        for arrow, tail_note, head_note in local_arrows:
            click.echo(
                f"  {format_arrow_text(tail_note)}  →  {format_arrow_text(head_note)}"
            )
        click.echo()


@cli.command()
@click.argument("query")
@click.option(
    "--page",
    default=None,
    help="Limit search to a single page (exact name, case-insensitive).",
)
@pass_store
def search(store: PametInMemoryStore, query: str, page: str | None) -> None:
    """Case-insensitive substring search across all notes. Returns matching
    notes with their page name and center coordinates. Use the coordinates
    with 'overview' or 'area' to explore the surrounding context."""
    query_lower = query.lower()
    results = []

    for pg in store.pages():
        if page and pg.name.lower() != page.lower():
            continue
        for note in store.notes(pg.id):
            text = note_text(note)
            if query_lower in text.lower():
                center = note.rect().center()
                results.append((pg.name, note, text, center.x(), center.y()))

    click.echo(f"Found {len(results)} notes matching '{query}':\n")
    for page_name, note, text, cx, cy in results:
        lines = text.split("\n")
        preview = lines[0][:120]
        if len(lines) > 1 or len(lines[0]) > 120:
            preview += "..."
        click.echo(f"  [{page_name}] ({cx:+.0f},{cy:+.0f})  {preview}")


# ---------------------------------------------------------------------------
# Diagnostic commands
# ---------------------------------------------------------------------------


@cli.command("bad-arrows")
@click.option(
    "--page",
    default=None,
    help="Limit to a single page (exact name, case-insensitive). "
    "Default: check all pages.",
)
@click.option(
    "--verbose", "-v", is_flag=True, help="Show arrow IDs and anchor details."
)
@pass_store
def bad_arrows(store: PametInMemoryStore, page: str | None, verbose: bool) -> None:
    """Find arrows with broken anchors (pointing to non-existent notes).

    Reports arrows whose tail or head note_anchor_id references a note
    that does not exist on the same page. Useful for diagnosing migration
    issues where notes are missing or arrows ended up in the wrong commit.
    """
    total_bad = 0
    pages_checked = 0

    for pg in sorted(store.pages(), key=lambda p: p.name):
        if page and pg.name.lower() != page.lower():
            continue
        pages_checked += 1

        notes_on_page = {n.id for n in store.notes(pg.id)}
        bad_on_page = []

        for arrow in store.arrows(pg.id):
            tail_id = arrow.tail.get("note_anchor_id")
            head_id = arrow.head.get("note_anchor_id")

            bad_tail = tail_id and tail_id not in notes_on_page
            bad_head = head_id and head_id not in notes_on_page

            if bad_tail or bad_head:
                bad_on_page.append((arrow, bad_tail, bad_head, tail_id, head_id))

        if bad_on_page:
            click.echo(f"\n[{pg.name}] — {len(bad_on_page)} bad arrow(s):")
            for arrow, bad_tail, bad_head, tail_id, head_id in bad_on_page:
                parts = []
                if bad_tail:
                    parts.append(f"tail→MISSING({tail_id})")
                if bad_head:
                    parts.append(f"head→MISSING({head_id})")
                label = ", ".join(parts)

                # Try to describe the valid end
                context_parts = []
                if not bad_tail and tail_id:
                    note = store.note(tail_id)
                    if note:
                        txt = note_text(note).split("\n")[0][:60]
                        context_parts.append(f"tail note: {txt}")
                if not bad_head and head_id:
                    note = store.note(head_id)
                    if note:
                        txt = note_text(note).split("\n")[0][:60]
                        context_parts.append(f"head note: {txt}")

                if verbose:
                    click.echo(f"  arrow_id={arrow.id}  {label}")
                    if context_parts:
                        click.echo(f"    {'; '.join(context_parts)}")
                else:
                    ctx = f"  ({'; '.join(context_parts)})" if context_parts else ""
                    click.echo(f"  {label}{ctx}")

            total_bad += len(bad_on_page)

    click.echo(
        f"\n--- Summary: {total_bad} bad arrows across {pages_checked} pages ---"
    )


@cli.command("overlapping-notes")
@click.option(
    "--page",
    default=None,
    help="Limit to a single page (exact name, case-insensitive). "
    "Default: check all pages.",
)
@click.option(
    "--min-overlap",
    type=float,
    default=0.5,
    help="Minimum overlap ratio (intersection area / smaller note area) "
    "to report. 0.5 = at least 50%% overlap. Use 0 for any overlap.",
)
@click.option(
    "--verbose", "-v", is_flag=True, help="Show note IDs and geometry details."
)
@pass_store
def overlapping_notes(
    store: PametInMemoryStore, page: str | None, min_overlap: float, verbose: bool
) -> None:
    """Find notes that significantly overlap each other on the same page.

    Reports pairs of notes whose bounding rectangles overlap by at least
    --min-overlap ratio (relative to the smaller note's area). Useful for
    detecting misplaced notes from migration bugs where notes from different
    time periods got stacked on top of each other.
    """
    total_overlaps = 0
    pages_checked = 0

    for pg in sorted(store.pages(), key=lambda p: p.name):
        if page and pg.name.lower() != page.lower():
            continue
        pages_checked += 1

        all_notes = python_list(store.notes(pg.id))
        if len(all_notes) < 2:
            continue

        overlaps_on_page = []

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
                    overlaps_on_page.append(
                        (all_notes[i], all_notes[j], ratio, intersection)
                    )

        if overlaps_on_page:
            # Sort by overlap ratio descending
            overlaps_on_page.sort(key=lambda x: x[2], reverse=True)
            click.echo(f"\n[{pg.name}] — {len(overlaps_on_page)} overlapping pair(s):")
            for note_a, note_b, ratio, inter in overlaps_on_page:
                text_a = note_text(note_a).split("\n")[0][:50]
                text_b = note_text(note_b).split("\n")[0][:50]
                ca = note_a.rect().center()
                cb = note_b.rect().center()

                if verbose:
                    click.echo(
                        f"  [{ratio:.0%} overlap] "
                        f"intersection: {inter.width():.0f}x{inter.height():.0f}"
                    )
                    click.echo(
                        f"    A: id={note_a.id} "
                        f"({ca.x():+.0f},{ca.y():+.0f}) "
                        f"{note_a.width:.0f}x{note_a.height:.0f}  "
                        f"{text_a}"
                    )
                    click.echo(
                        f"    B: id={note_b.id} "
                        f"({cb.x():+.0f},{cb.y():+.0f}) "
                        f"{note_b.width:.0f}x{note_b.height:.0f}  "
                        f"{text_b}"
                    )
                else:
                    click.echo(
                        f"  [{ratio:.0%}] "
                        f'({ca.x():+.0f},{ca.y():+.0f}) "{text_a}" ∩ '
                        f'({cb.x():+.0f},{cb.y():+.0f}) "{text_b}"'
                    )

            total_overlaps += len(overlaps_on_page)

    click.echo(
        f"\n--- Summary: {total_overlaps} overlapping pairs across "
        f"{pages_checked} pages (threshold: {min_overlap:.0%}) ---"
    )


if __name__ == "__main__":
    cli()
