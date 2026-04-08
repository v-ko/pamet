"""File blob storage adapter.

Owns the on-disk file blob I/O and the ``FileIndex`` content-hash cache.
Composed into ``ProjectFolderManager`` as ``pfm.file_storage``.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path, PurePosixPath

from fusion.logging import get_logger

from pamet.model.file_item import FileItem
from pamet.storage.file_index import FileIndex
from pamet.storage.pamet_in_memory_store import PametInMemoryStore

log = get_logger(__name__)


class FileStorageAdapter:
    """Blob storage for FileItem entities within a project repo."""

    def __init__(self, repo_root: Path, store: PametInMemoryStore) -> None:
        self._repo_root = repo_root
        self._store = store
        self._index = FileIndex(repo_root / ".pamet" / "file-index.db")

    # -- Lifecycle -------------------------------------------------------------

    def rebuild_index(self, file_items: Iterable[FileItem]) -> None:
        """Rebuild the content-hash index for the given *file_items*."""
        referenced: dict[str, Path] = {}
        for fi in file_items:
            rel = fi.path
            if not rel:
                continue
            try:
                abs_path = self._resolve_path(PurePosixPath(rel))
            except ValueError:
                continue
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
    ) -> None:
        """Write a file blob at the project-relative path.

        Raises ``FileExistsError`` if a file already exists at that path.
        """
        dest = self._resolve_path(relative_path)
        if dest.exists():
            raise FileExistsError(f"File already exists at {relative_path}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        self._index.put(relative_path.as_posix(), dest)

    def find_path(self, file_item_id: str) -> Path | None:
        """Resolve the on-disk path for a FileItem.

        Returns ``None`` if the entity is missing, has no path,
        or the file doesn't exist on disk.
        """
        entity = self._store.find_one(id=file_item_id)
        if entity is None:
            return None
        rel_path = getattr(entity, "path", None)
        if not isinstance(rel_path, str) or not rel_path:
            return None
        path = self._resolve_path(PurePosixPath(rel_path))
        if not path.exists():
            return None
        return path

    def remove(self, file_item_id: str) -> bool:
        """Delete a file blob from disk. Returns ``True`` if deleted."""
        path = self.find_path(file_item_id)
        if path is None:
            return False
        rel_path = path.relative_to(self._repo_root).as_posix()
        path.unlink()
        self._index.remove(rel_path)
        return True
