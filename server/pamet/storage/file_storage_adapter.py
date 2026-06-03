"""File blob storage adapter.

Owns the on-disk file blob I/O and the ``FileIndex`` content-hash cache.
Composed into ``ProjectFolderManager`` as ``pfm.file_storage``.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from sivkit.logging import get_logger

from pamet.model.note import Note
from pamet.storage.file_index import FileIndex

log = get_logger(__name__)


class FileStorageAdapter:
    """Blob storage for media files within a project repo."""

    def __init__(self, repo_root: Path, store) -> None:
        self._repo_root = repo_root
        self._store = store
        self._index = FileIndex(repo_root / ".pamet" / "file-index.db")

    # -- Lifecycle -------------------------------------------------------------

    def rebuild_index_from_store(self, store) -> None:
        """Rebuild the content-hash index from image paths referenced in notes."""
        referenced: dict[str, Path] = {}
        for entity in store.find():
            if not isinstance(entity, Note):
                continue
            image_ref = getattr(entity, "content", {}).get("image")
            if not image_ref or not image_ref.get("path"):
                continue
            rel = image_ref["path"]
            try:
                abs_path = self._resolve_path(PurePosixPath(rel))
            except ValueError:
                continue
            if abs_path.exists():
                referenced[rel] = abs_path
        self._index.rebuild(referenced)

    def close(self) -> None:
        self._index.close()

    # -- Path resolution -------------------------------------------------------

    def _resolve_path(self, relative_path: PurePosixPath) -> Path:
        """Convert a repo-relative posix path to an absolute filesystem path.

        Rejects absolute paths and directory traversals.
        """
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise ValueError(f"Invalid file path (not pure relative): {relative_path}")
        return self._repo_root / Path(*relative_path.parts)

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
        dest = self._resolve_path(relative_path)
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
            path = self._resolve_path(PurePosixPath(relative_path))
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
            path = self._resolve_path(PurePosixPath(relative_path))
        except ValueError:
            return False
        if not path.exists():
            return False
        path.unlink()
        self._index.remove(relative_path)
        return True
