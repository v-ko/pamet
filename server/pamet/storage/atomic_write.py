"""Atomic file writes: a failed write leaves the old file intact."""

from __future__ import annotations

import contextlib
import os
import shutil
from pathlib import Path

# Written next to the target and replaced onto it; leftovers are deleted at load
TEMP_SUFFIX = ".tmp"


def atomic_write(path: Path, data: bytes) -> None:
    """Blocking: write *data* to a temp file, then replace *path* with it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + TEMP_SUFFIX)
    try:
        with open(temp, "wb") as file:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        if path.exists():
            shutil.copymode(path, temp)
        os.replace(temp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            temp.unlink(missing_ok=True)
        raise
