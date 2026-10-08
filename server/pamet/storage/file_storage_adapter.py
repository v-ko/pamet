"""File blob storage adapter.

Owns the on-disk file blob I/O and the ``FileIndex`` content-hash cache.
Composed into ``ProjectFolderManager`` as ``pfm.file_storage``.
"""

from __future__ import annotations

import logging
from pathlib import Path, PurePosixPath
from typing import Iterable

from sivkit.libs.model import Entity

from pamet.model.note import Note
from pamet.storage.file_index import FileIndex

log = logging.getLogger(__name__)


def _index_path(repo_root: Path) -> Path:
    return repo_root / ".pamet" / "file-index.db"


def _resolve_path(repo_root: Path, relative_path: PurePosixPath) -> Path:
    """Convert a repo-relative posix path to an absolute filesystem path.

    Rejects absolute paths and directory traversals.
    """
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValueError(f"Invalid file path (not pure relative): {relative_path}")
    return repo_root / Path(*relative_path.parts)


def rebuild_file_index(repo_root: Path, entities: Iterable[Entity]) -> None:
    """Rebuild the content-hash index from image paths referenced in notes."""
    referenced: dict[str, Path] = {}
    for entity in entities:
        if not isinstance(entity, Note):
            continue
        image_ref = getattr(entity, "content", {}).get("image")
        if not image_ref or not image_ref.get("path"):
            continue
        rel = image_ref["path"]
        try:
            abs_path = _resolve_path(repo_root, PurePosixPath(rel))
        except ValueError:
            continue
        if abs_path.exists():
            referenced[rel] = abs_path

    index = FileIndex(_index_path(repo_root))
    try:
        index.rebuild(referenced)
    finally:
        index.close()


class FileStorageAdapter:
    """Blob storage for media files within a project repo."""

    def __init__(self, repo_root: Path, store) -> None:
        self._repo_root = repo_root
        self._store = store
        self._index = FileIndex(_index_path(repo_root))

    # -- Lifecycle -------------------------------------------------------------

    def close(self) -> None:
        self._index.close()

    # -- Blob I/O --------------------------------------------------------------

    def add(
        self,
        relative_path: PurePosixPath,
        data: bytes,
    ) -> str:
        """Write a file blob at the project-relative path.

        Raises ``FileExistsError`` if a file already exists at that path.
        Returns the content hash.
        """
        dest = _resolve_path(self._repo_root, relative_path)
        if dest.exists():
            raise FileExistsError(f"File already exists at {relative_path}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return self._index.put(relative_path.as_posix(), dest)

    def get_path(self, relative_path: str) -> Path | None:
        """Resolve the on-disk path for a project-relative path.

        Returns ``None`` if the file doesn't exist on disk.
        """
        try:
            path = _resolve_path(self._repo_root, PurePosixPath(relative_path))
        except ValueError:
            return None
        if not path.exists():
            return None
        return path

    def get_hash(self, relative_path: str) -> str | None:
        """Return the cached content hash for a project-relative path."""
        return self._index.get_hash(relative_path)

    def remove_by_path(self, relative_path: str) -> bool:
        """Delete a file blob from disk by path. Returns ``True`` if deleted."""
        try:
            path = _resolve_path(self._repo_root, PurePosixPath(relative_path))
        except ValueError:
            return False
        if not path.exists():
            return False
        path.unlink()
        self._index.remove(relative_path)
        return True
