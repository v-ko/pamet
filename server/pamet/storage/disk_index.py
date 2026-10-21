"""What Pamet knows about files on disk."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from sivkit.storage.fs.ops import Fingerprint, fingerprint


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


def file_fingerprint(path: Path) -> Fingerprint | None:
    """None if the file is missing or can't be statted."""
    try:
        return fingerprint(path)
    except OSError:
        return None
