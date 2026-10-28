"""File blob storage adapter.

Owns the on-disk file blob I/O and the ``FileIndex`` content-hash cache.
Composed into ``ProjectFolderManager`` as ``pfm.file_storage``.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Iterable

from sivkit.libs.model import Entity
from sivkit.storage.fs.ops import (
    UnsafePath,
    check_new_path,
    create_new,
    delete,
    make_folder,
    resolve_in_root,
)

from pamet.model.note import Note
from pamet.storage.content_paths import check_media_path
from pamet.storage.file_index import FileIndex, content_hash

log = logging.getLogger(__name__)


def _index_path(repo_root: Path) -> Path:
    return repo_root / ".pamet" / "file-index.db"


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
            check_media_path(rel)
            abs_path = resolve_in_root(repo_root, rel)
        except (UnsafePath, OSError):
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
        # One media write at a time: keeps the case check, the disk and the index in order
        self._lock = asyncio.Lock()

    # -- Lifecycle -------------------------------------------------------------

    def close(self) -> None:
        """Release the index after admitted operations have drained."""
        self._index.close()

    # -- Blob I/O --------------------------------------------------------------

    async def add(self, rel: str, data: bytes) -> str:
        """Write a new file blob at the project-relative path; returns its content hash.

        Raises `UnsafePath`, `UnsafeName`, or `Conflict` if a file is already there.
        """
        check_media_path(rel)
        async with self._lock:
            hash_, mtime_ns = await asyncio.to_thread(
                _write_new, self._repo_root, rel, data
            )
            self._index.put(rel, hash_, mtime_ns)
            return hash_

    def get_path(self, relative_path: str) -> Path | None:
        """Resolve the on-disk path for a project-relative path.

        Returns ``None`` if the file doesn't exist on disk.
        """
        try:
            check_media_path(relative_path)
            path = resolve_in_root(self._repo_root, relative_path)
        except UnsafePath:
            return None
        if not path.exists():
            return None
        return path

    def get_hash(self, relative_path: str) -> str | None:
        """Return the cached content hash for a project-relative path."""
        return self._index.get_hash(relative_path)

    async def remove_by_path(self, rel: str) -> bool:
        """Delete a file blob from disk by path. Returns ``True`` if deleted."""
        check_media_path(rel)
        async with self._lock:
            deleted = await asyncio.to_thread(_delete, self._repo_root, rel)
            if deleted:
                self._index.remove(rel)
            return deleted


def _write_new(root: Path, rel: str, data: bytes) -> tuple[str, int]:
    """Blocking: create the file and its missing folders. Returns (hash, mtime_ns)."""
    path = resolve_in_root(root, rel)
    check_new_path(root, rel)
    parts = rel.split("/")
    for i in range(1, len(parts)):
        make_folder(root.joinpath(*parts[:i]))
    return content_hash(data), create_new(path, data).mtime_ns


def _delete(root: Path, rel: str) -> bool:
    path = resolve_in_root(root, rel)
    if not path.is_file():
        return False
    delete(path)
    return True
