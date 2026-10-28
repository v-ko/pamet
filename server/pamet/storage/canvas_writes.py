"""Canvas file rules on top of SivKit's file changes: path checks, page writes."""

from __future__ import annotations

import asyncio
from pathlib import Path

from sivkit.storage.fs.changes import (
    ApplyResult,
    Create,
    Delete,
    Rename,
    Replace,
    apply,
)
from sivkit.storage.fs.names import UnsafeName, check_portable_name
from sivkit.storage.fs.ops import (
    Conflict,
    UnsafePath,
    check_new_path,
    make_folder,
    resolve_in_root,
)

from pamet.services.constants import CANVAS_FILE_EXT
from pamet.storage.content_paths import is_metadata_path
from pamet.storage.project_walk import IGNORED_DIRS, matches_exclude

PageWrite = Create | Replace | Rename


class SaveRejected(ValueError):
    """A save that would write an invalid or colliding path; nothing changed."""


def check_page_path(rel: object, exclude_patterns: list[str]) -> None:
    """Pure check of a relative page path; the file system isn't touched.

    Only the file name must be portable: folders may already exist with any
    name, and new ones are checked when a save creates them.
    """
    if not isinstance(rel, str) or not rel.endswith(CANVAS_FILE_EXT) or "\\" in rel:
        raise SaveRejected(f"Invalid page path: {rel!r}")
    if is_metadata_path(rel):
        raise SaveRejected(f"Page path is in Pamet metadata: {rel!r}")
    parts = rel.split("/")
    for i, part in enumerate(parts):
        if part in ("", ".", ".."):
            raise SaveRejected(f"Invalid page path: {rel!r}")
        is_folder = i < len(parts) - 1
        if (is_folder and part in IGNORED_DIRS) or matches_exclude(
            part, "/".join(parts[: i + 1]), exclude_patterns
        ):
            raise SaveRejected(f"Page path is in an ignored folder: {rel!r}")
    try:
        check_portable_name(parts[-1])
    except UnsafeName as e:
        raise SaveRejected(f"Not a portable file name ({e.reason}): {rel!r}") from None


def target(change: PageWrite | Delete) -> str:
    return change.new if isinstance(change, Rename) else change.rel


def rename_cycles(renames: dict[str, str]) -> set[str]:
    """The old paths of renames (old → new) that form cycles, as pages swapping paths."""
    in_cycle: set[str] = set()
    for start in renames:
        path, seen = renames[start], {start}
        while path in renames and path not in seen:
            seen.add(path)
            path = renames[path]
        if path == start:
            in_cycle |= seen
    return in_cycle


async def write_changes(
    root: Path, deletes: list[Delete], writes: list[PageWrite]
) -> tuple[list[ApplyResult], list[ApplyResult]]:
    """Create missing folders, then run the deletes, then the writes.

    Changes in a group run concurrently, and a failed one doesn't stop the
    others. A write into a folder that couldn't be made gets that error.
    """
    folders = {
        "/".join(parts[:i])
        for parts in (target(w).split("/")[:-1] for w in writes)
        for i in range(1, len(parts) + 1)
    }
    errors = await asyncio.to_thread(_make_folders, root, folders) if folders else {}

    async def write(change: PageWrite) -> ApplyResult:
        error = errors.get(target(change).rpartition("/")[0])
        return ApplyResult(change, error=error) if error else await apply(root, change)

    deleted = await asyncio.gather(*(apply(root, d) for d in deletes))
    written = await asyncio.gather(*(write(w) for w in writes))
    return list(deleted), list(written)


def _make_folders(root: Path, rels: set[str]) -> dict[str, Exception]:
    """Blocking: create the missing folders, parents first. Returns errors by folder."""
    errors: dict[str, Exception] = {}
    for rel in sorted(rels, key=lambda r: r.count("/")):
        parent = rel.rpartition("/")[0]
        if parent in errors:
            errors[rel] = errors[parent]
            continue
        try:
            path = resolve_in_root(root, rel)
            if not path.is_dir():
                check_new_path(root, rel)
                make_folder(path)
        except (UnsafeName, UnsafePath, Conflict, OSError) as e:
            errors[rel] = e
    return errors
