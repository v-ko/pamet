"""Persistent file content-hash index backed by SQLite (via SQLAlchemy).

Caches SHA-256 content hashes keyed by repo-relative path, with an mtime_ns
guard so that hashes are only recomputed when the file has actually changed on
disk.  Lives at ``.pamet/file-index.db`` inside each project repo.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from sivkit.storage.sqlite_engine import create_sqlite_engine
from sqlalchemy import BigInteger, Insert, Text, delete, insert, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from pamet.services.constants import CONTENT_HASH_HEX_LEN


class _Base(DeclarativeBase):
    pass


class FileIndexEntry(_Base):
    __tablename__ = "fileindexentry"  # the name peewee created
    rel_path: Mapped[str] = mapped_column(Text, primary_key=True)
    hash: Mapped[str] = mapped_column(Text)
    mtime_ns: Mapped[int] = mapped_column(BigInteger)


class FileIndex:
    """Per-project file content-hash index."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._engine = create_sqlite_engine(db_path)
        _Base.metadata.create_all(self._engine)
        self._session = sessionmaker(self._engine)

    def close(self) -> None:
        self._engine.dispose()

    # -- Bulk rebuild ----------------------------------------------------------

    def rebuild(self, referenced: dict[str, Path]) -> None:
        """Rebuild the index for *referenced* files.

        *referenced* maps repo-relative posix paths to absolute filesystem
        paths.  Entries not in *referenced* are pruned.  Hashes are only
        recomputed when mtime_ns differs from the cached value.
        """
        with self._session.begin() as s:
            # Prune stale entries
            s.execute(
                delete(FileIndexEntry).where(
                    FileIndexEntry.rel_path.not_in(list(referenced.keys()))
                )
            )

            for rel, abs_path in referenced.items():
                try:
                    st = abs_path.stat()
                except OSError:
                    s.execute(
                        delete(FileIndexEntry).where(FileIndexEntry.rel_path == rel)
                    )
                    continue

                mtime_ns = st.st_mtime_ns
                cached_mtime_ns = s.scalar(
                    select(FileIndexEntry.mtime_ns).where(
                        FileIndexEntry.rel_path == rel
                    )
                )
                if cached_mtime_ns == mtime_ns:
                    continue

                s.execute(_replace_entry(rel, _compute_hash(abs_path), mtime_ns))

    # -- Single-entry operations -----------------------------------------------

    def get_hash(self, rel_path: str) -> str | None:
        with self._session() as s:
            return s.scalar(
                select(FileIndexEntry.hash).where(FileIndexEntry.rel_path == rel_path)
            )

    def put(self, rel_path: str, abs_path: Path) -> str:
        """Compute hash, store entry, return the hash."""
        st = abs_path.stat()
        content_hash = _compute_hash(abs_path)
        with self._session.begin() as s:
            s.execute(_replace_entry(rel_path, content_hash, st.st_mtime_ns))
        return content_hash

    def remove(self, rel_path: str) -> None:
        with self._session.begin() as s:
            s.execute(delete(FileIndexEntry).where(FileIndexEntry.rel_path == rel_path))


def _replace_entry(rel_path: str, content_hash: str, mtime_ns: int) -> Insert:
    return (
        insert(FileIndexEntry)
        .prefix_with("OR REPLACE")
        .values(rel_path=rel_path, hash=content_hash, mtime_ns=mtime_ns)
    )


def _compute_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:CONTENT_HASH_HEX_LEN]
