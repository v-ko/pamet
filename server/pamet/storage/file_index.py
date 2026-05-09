"""Persistent file content-hash index backed by SQLite (via peewee).

Caches SHA-256 content hashes keyed by repo-relative path, with an mtime_ns
guard so that hashes are only recomputed when the file has actually changed on
disk.  Lives at ``.pamet/file-index.db`` inside each project repo.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import peewee as pw

from pamet.services.constants import CONTENT_HASH_HEX_LEN


class FileIndexEntry(pw.Model):
    rel_path: str = pw.TextField(primary_key=True)  # type: ignore[assignment]
    hash: str = pw.TextField()  # type: ignore[assignment]
    mtime_ns: int = pw.BigIntegerField()  # type: ignore[assignment]


_ALL_MODELS = [FileIndexEntry]


class FileIndex:
    """Per-project file content-hash index."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db = pw.SqliteDatabase(str(db_path), pragmas={"journal_mode": "wal"})
        self._db.connect()
        with self._db.bind_ctx(_ALL_MODELS):
            self._db.create_tables(_ALL_MODELS)

    def _ctx(self):
        return self._db.bind_ctx(_ALL_MODELS)

    def close(self) -> None:
        if not self._db.is_closed():
            self._db.close()

    # -- Bulk rebuild ----------------------------------------------------------

    def rebuild(self, referenced: dict[str, Path]) -> None:
        """Rebuild the index for *referenced* files.

        *referenced* maps repo-relative posix paths to absolute filesystem
        paths.  Entries not in *referenced* are pruned.  Hashes are only
        recomputed when mtime_ns differs from the cached value.
        """
        with self._ctx(), self._db.atomic():
            # Prune stale entries
            (
                FileIndexEntry.delete()
                .where(FileIndexEntry.rel_path.not_in(list(referenced.keys())))
                .execute()
            )

            for rel, abs_path in referenced.items():
                try:
                    st = abs_path.stat()
                except OSError:
                    FileIndexEntry.delete_by_id(rel)
                    continue

                mtime_ns = st.st_mtime_ns
                existing = FileIndexEntry.get_or_none(FileIndexEntry.rel_path == rel)
                if existing and existing.mtime_ns == mtime_ns:
                    continue

                content_hash = _compute_hash(abs_path)
                FileIndexEntry.replace(
                    rel_path=rel,
                    hash=content_hash,
                    mtime_ns=mtime_ns,
                ).execute()

    # -- Single-entry operations -----------------------------------------------

    def get_hash(self, rel_path: str) -> str | None:
        with self._ctx():
            entry = FileIndexEntry.get_or_none(FileIndexEntry.rel_path == rel_path)
            return entry.hash if entry else None

    def put(self, rel_path: str, abs_path: Path) -> str:
        """Compute hash, store entry, return the hash."""
        st = abs_path.stat()
        content_hash = _compute_hash(abs_path)
        with self._ctx():
            FileIndexEntry.replace(
                rel_path=rel_path,
                hash=content_hash,
                mtime_ns=st.st_mtime_ns,
            ).execute()
        return content_hash

    def remove(self, rel_path: str) -> None:
        with self._ctx():
            FileIndexEntry.delete_by_id(rel_path)


def _compute_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:CONTENT_HASH_HEX_LEN]
