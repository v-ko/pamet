"""What Pamet knows about files on disk."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Fingerprint = tuple[int, int, int]  # size, mtime_ns, inode


@dataclass
class DiskEntry:
    """What Pamet last knew about one canvas file on disk.

    An owner's entities are in the store; a duplicate's ids are owned by
    another file. A file that never loaded has no role.
    """

    fingerprint: Fingerprint | None  # None if the file couldn't be statted
    role: Literal["owner", "duplicate"] | None = None
    read_error: str | None = None
    ids: tuple[str, ...] = ()  # The page id first, then its children's


def fingerprint(st: os.stat_result) -> Fingerprint:
    return (st.st_size, st.st_mtime_ns, st.st_ino)


def file_fingerprint(path: Path) -> Fingerprint | None:
    try:
        return fingerprint(path.stat())
    except OSError:
        return None
