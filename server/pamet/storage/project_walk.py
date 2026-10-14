"""Shared utilities for walking a Pamet project folder.

Extracted from ProjectFolderManager so the same ignore/exclude logic
can be reused by read-only tools (CLI, etc.) without spinning up
watchers, backups, or migrations.
"""

from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path
from typing import Callable, Iterator

from pamet.services.constants import CANVAS_FILE_EXT, MAX_WALK_ENTRIES
from pamet.storage.migrations.manager import MIGRATION_BACKUP_DIR_NAMES

IGNORED_DIRS = {".pamet"} | MIGRATION_BACKUP_DIR_NAMES


def matches_exclude(name: str, rel_path: str, patterns: list[str]) -> bool:
    """Match a file/dir name against exclude patterns.

    Supports:
      - bare names/globs: matched against the basename (e.g. "build", "*.tmp")
      - **/name patterns: matched against the basename (any depth)
      - path patterns (contain /): matched against the relative path from repo root
    """
    for pat in patterns:
        if pat.startswith("**/"):
            if fnmatch(name, pat[3:]):
                return True
        elif "/" in pat:
            if fnmatch(rel_path, pat):
                return True
        else:
            if fnmatch(name, pat):
                return True
    return False


class ProjectTooLargeError(Exception):
    """Raised when a project folder exceeds the walk budget."""


def walk_project(
    repo_root: Path,
    exclude_patterns: list[str] | None = None,
    root: Path | None = None,
    *,
    budget: list[int] | None = None,
    onerror: Callable[[Path, OSError], None] | None = None,
) -> Iterator[Path]:
    """Recursively yield all non-ignored paths under *root*.

    Yields both directories and files.  Directories are yielded before
    their contents (pre-order). A folder that can't be listed is skipped
    and reported to *onerror*.
    """
    if exclude_patterns is None:
        exclude_patterns = []
    if root is None:
        root = repo_root
    if budget is None:
        budget = [MAX_WALK_ENTRIES]

    try:
        entries = sorted(root.iterdir(), key=lambda p: p.name)
    except OSError as exc:
        if onerror is not None:
            onerror(root, exc)
        return

    for entry in entries:
        budget[0] -= 1
        if budget[0] <= 0:
            raise ProjectTooLargeError(
                f"Project folder {repo_root} exceeds the walk "
                f"budget of {MAX_WALK_ENTRIES} filesystem entries"
            )

        if entry.is_symlink():
            continue

        rel = entry.relative_to(repo_root).as_posix()

        if entry.is_dir():
            if entry.name in IGNORED_DIRS:
                continue
            if matches_exclude(entry.name, rel, exclude_patterns):
                continue
            yield entry
            yield from walk_project(
                repo_root, exclude_patterns, entry, budget=budget, onerror=onerror
            )
        else:
            if matches_exclude(entry.name, rel, exclude_patterns):
                continue
            yield entry


def iter_canvas_paths(
    repo_root: Path,
    exclude_patterns: list[str] | None = None,
    *,
    onerror: Callable[[Path, OSError], None] | None = None,
) -> Iterator[Path]:
    """Yield all .canvas file paths in the project, respecting ignores."""
    for path in walk_project(repo_root, exclude_patterns, onerror=onerror):
        if not path.is_dir() and path.name.endswith(CANVAS_FILE_EXT):
            yield path
