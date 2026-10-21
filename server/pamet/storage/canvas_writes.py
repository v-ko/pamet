"""Canvas file rules on top of atomic_write: path checks, conflicts, page writes."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from sivkit.storage.fs.names import UnsafeName, check_portable_name

from pamet.services.constants import CANVAS_FILE_EXT
from pamet.storage.atomic_write import atomic_write
from pamet.storage.disk_index import Fingerprint, file_fingerprint
from pamet.storage.project_walk import IGNORED_DIRS, matches_exclude


class SaveRejected(ValueError):
    """A save that would write an invalid or conflicting path; nothing changed."""


@dataclass(frozen=True)
class PageMove:
    """A page created at *rel*, or renamed from *old_rel* to it."""

    page_id: str
    rel: str
    old_rel: str | None


@dataclass(frozen=True)
class PageWrite:
    rel: str
    data: bytes
    ids: tuple[str, ...]  # The page id first, then its children's
    old_rel: str | None = None  # The page's file before a rename


def check_page_path(rel: object, exclude_patterns: list[str]) -> None:
    """Pure check of a relative page path; the file system isn't touched.

    Only the file name must be portable: folders may already exist with any
    name, and new ones are checked when a save creates them.
    """
    if not isinstance(rel, str) or not rel.endswith(CANVAS_FILE_EXT) or "\\" in rel:
        raise SaveRejected(f"Invalid page path: {rel!r}")
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


def check_targets(root: Path, moves: list[PageMove]) -> None:
    """Blocking: refuse a target that holds another file than the page's own."""
    for move in moves:
        target = root / move.rel
        if not target.exists():
            continue
        if move.old_rel is None or not _same_file(root / move.old_rel, target):
            raise SaveRejected(f"Another file exists at {move.rel!r}")


def write_pages(
    root: Path, writes: list[PageWrite], deletes: list[str]
) -> tuple[dict[str, Fingerprint | None], OSError | None]:
    """Blocking: delete files, then write pages; stop at the first error.

    Returns every touched path as it is on disk afterwards, with the error.
    """
    error = None
    try:
        for rel in deletes:
            (root / rel).unlink(missing_ok=True)
        for write in writes:
            target = root / write.rel
            old = root / write.old_rel if write.old_rel else None
            if old is not None and _same_file(old, target):
                # Case-only rename: deleting the old path would delete the file
                atomic_write(old, write.data)
                os.rename(old, target)
            else:
                atomic_write(target, write.data)
                if old is not None:
                    old.unlink(missing_ok=True)
    except OSError as exc:
        error = exc

    touched = [w.rel for w in writes] + [w.old_rel for w in writes if w.old_rel]
    stats = {rel: file_fingerprint(root / rel) for rel in deletes + touched}
    for write in writes:
        # Where names ignore case, the old path still finds the renamed file
        if write.old_rel and stats[write.old_rel] == stats[write.rel]:
            stats[write.old_rel] = None
    return stats, error


def _same_file(a: Path, b: Path) -> bool:
    try:
        return os.path.samefile(a, b)
    except FileNotFoundError:
        return False
