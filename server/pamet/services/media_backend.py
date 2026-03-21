from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Optional, Dict, Tuple
import hashlib
import time

from pamet.services.constants import CONTENT_HASH_HEX_LEN, DEFAULT_TRASH_RETENTION_S
from pamet.services.media_utils import parse_trash_stem, build_trash_filename
from peewee import Model, TextField, IntegerField, SqliteDatabase

# No FastAPI dependencies here; this is a pure service


class MediaCachePW(Model):
    path = TextField(unique=True)
    mtime = IntegerField()
    hash = TextField()


class MediaItemPW(Model):
    media_id = TextField(unique=True)
    rel_path = TextField()
    content_hash = TextField()
    trashed = IntegerField(default=0)
    updated_at = IntegerField(default=0)


@dataclass
class BlobStorageAdapter:
    """
    Desktop media backend that stores files directly in the project folder.

    Files are addressed by ``FileItem.path`` (relative to the project root),
    while lookup metadata is persisted in ``<repo>/pamet.db``.
    """
    repo_root: Path
    project_manager: object | None = None  # ProjectFolderManager runtime owner

    TRASH_DIR: str = "media-backup"

    def __post_init__(self):
        self.repo_root = Path(self.repo_root)
        self.pamet_dir = self.repo_root / '.pamet'
        self.pamet_dir.mkdir(parents=True, exist_ok=True)
        self.trash_dir = self.pamet_dir / self.TRASH_DIR
        self.trash_dir.mkdir(parents=True, exist_ok=True)

        # Shared project-level DB for media metadata/cache.
        self._db = SqliteDatabase(str(self.repo_root / 'pamet.db'))
        with self._db.bind_ctx([MediaCachePW, MediaItemPW]):
            self._db.create_tables([MediaCachePW, MediaItemPW], safe=True)

        # Runtime indices for trashed items: (id, hash) -> list[(expiry_ts, path)]
        self._trash_index: Dict[Tuple[str, str], list[Tuple[int, Path]]] = {}
        self._scan_trash_folder()

    def _resolve_relative_path(self, relative_path: str) -> Path:
        if not relative_path:
            raise ValueError("Media path is required")

        raw = relative_path.strip()
        if not raw:
            raise ValueError("Media path is required")

        posix_path = PurePosixPath(raw)
        if posix_path.is_absolute():
            raise ValueError(f"Invalid media path: {relative_path}")

        if ".." in posix_path.parts:
            raise ValueError(f"Invalid media path: {relative_path}")

        rel = Path(*posix_path.parts)
        return self.repo_root / rel

    def _relative_path_for_disk_path(self, path: Path) -> str:
        return str(path.relative_to(self.repo_root)).replace("\\", "/")

    def _upsert_media_item(
        self, media_id: str, rel_path: str, content_hash: str, trashed: int = 0
    ) -> None:
        now = int(time.time())
        with self._db.bind_ctx([MediaItemPW]):
            with self._db.atomic():
                rec = MediaItemPW.get_or_none(MediaItemPW.media_id == media_id)
                if rec is None:
                    MediaItemPW.create(
                        media_id=media_id,
                        rel_path=rel_path,
                        content_hash=content_hash,
                        trashed=trashed,
                        updated_at=now,
                    )
                else:
                    rec.rel_path = rel_path
                    rec.content_hash = content_hash
                    rec.trashed = trashed
                    rec.updated_at = now
                    rec.save()

    def _media_item_row(self, media_id: str):
        with self._db.bind_ctx([MediaItemPW]):
            return MediaItemPW.get_or_none(MediaItemPW.media_id == media_id)

    def _resolve_disk_path_for_media_id(self, media_id: str) -> Path | None:
        item = self._media_item_row(media_id)
        if item is None:
            return None

        try:
            return self._resolve_relative_path(str(item.rel_path))
        except ValueError:
            return None

    def compute_and_cache_hash(self, path: Path) -> str:
        data = path.read_bytes()
        full = hashlib.sha256(data).hexdigest()
        short = full[:CONTENT_HASH_HEX_LEN]
        mtime = int(path.stat().st_mtime)
        # Upsert behavior: try fetch; if present -> update; else create
        with self._db.bind_ctx([MediaCachePW]):
            with self._db.atomic():
                rec = MediaCachePW.get_or_none(MediaCachePW.path == str(path))
                if rec is None:
                    MediaCachePW.create(path=str(path), mtime=mtime, hash=short)
                else:
                    rec.mtime = mtime
                    rec.hash = short
                    rec.save()
        return short

    def _store_known_hash(self, path: Path, content_hash: str) -> None:
        mtime = int(path.stat().st_mtime)
        with self._db.bind_ctx([MediaCachePW]):
            with self._db.atomic():
                rec = MediaCachePW.get_or_none(MediaCachePW.path == str(path))
                if rec is None:
                    MediaCachePW.create(path=str(path), mtime=mtime, hash=content_hash)
                else:
                    rec.mtime = mtime
                    rec.hash = content_hash
                    rec.save()

    def get_cached_hash(self, path: Path) -> Optional[str]:
        mtime = int(path.stat().st_mtime)
        with self._db.bind_ctx([MediaCachePW]):
            rec = MediaCachePW.get_or_none(MediaCachePW.path == str(path))
            if rec is None:
                return None
            if int(rec.mtime) != mtime:
                return None
            return str(rec.hash)

    # ----- Trash helpers -----
    def _scan_trash_folder(self):
        self._trash_index.clear()
        for entry in self.trash_dir.iterdir():
            if not entry.is_file():
                continue
            stem = entry.stem  # without extension
            media_id, content_hash, expiry = parse_trash_stem(stem)
            if not media_id or not content_hash:
                continue
            key = (media_id, content_hash)
            self._trash_index.setdefault(key, []).append((expiry, entry))
        # Sort by expiry ascending for determinism
        for key in self._trash_index:
            self._trash_index[key].sort(key=lambda t: t[0])

    # --- High-level operations used by the API layer ---
    def _move_existing_path_to_trash(
        self,
        src: Path,
        media_id: str,
        content_hash: str,
        retention_s: int | None = None,
    ) -> bool:
        if not src.exists():
            return False

        expiry = int(time.time()) + int(retention_s or DEFAULT_TRASH_RETENTION_S)
        dst = self.trash_dir / build_trash_filename(media_id, content_hash, expiry, src.suffix)
        src.rename(dst)
        key = (media_id, content_hash)
        self._trash_index.setdefault(key, []).append((expiry, dst))
        self._trash_index[key].sort(key=lambda t: t[0])
        return True

    def save_bytes(
        self,
        media_id: str,
        content_hash: str,
        relative_path: str,
        data: bytes,
        mime_type: Optional[str],
    ) -> None:
        """Persist a media blob at the project-relative FileItem path."""
        del mime_type
        dest = self._resolve_relative_path(relative_path)
        dest.parent.mkdir(parents=True, exist_ok=True)

        if dest.exists():
            current_hash = self.get_cached_hash(dest)
            if current_hash is None:
                current_hash = self.compute_and_cache_hash(dest)
            if current_hash != content_hash:
                self._move_existing_path_to_trash(dest, media_id, current_hash)

        dest.write_bytes(data)
        self._store_known_hash(dest, content_hash)
        self._upsert_media_item(
            media_id,
            self._relative_path_for_disk_path(dest),
            content_hash,
            trashed=0,
        )

    def find_item_path(self, media_id: str, content_hash: str) -> Path | None:
        """Resolve the active file path for an item, validating its current hash."""
        item = self._media_item_row(media_id)
        if item is None or int(item.trashed) == 1:
            return None
        if str(item.content_hash) != content_hash:
            return None

        path = self._resolve_disk_path_for_media_id(media_id)
        if path is None or not path.exists():
            return None

        cached_hash = self.get_cached_hash(path)
        current_hash = cached_hash if cached_hash is not None else self.compute_and_cache_hash(path)
        if current_hash != content_hash:
            return None
        return path

    def move_to_trash(self, media_id: str, content_hash: str, retention_s: int | None = None) -> bool:
        """Move the current file version to the trash backup folder."""
        src = self.find_item_path(media_id, content_hash)
        if src is None:
            return False
        moved = self._move_existing_path_to_trash(src, media_id, content_hash, retention_s)
        if moved:
            item = self._media_item_row(media_id)
            if item is not None:
                self._upsert_media_item(
                    media_id,
                    str(item.rel_path),
                    str(item.content_hash),
                    trashed=1,
                )
        return moved

    def restore_from_trash(self, media_id: str, content_hash: str) -> bool:
        """Restore an item from trash to its active path. Returns True if restored."""
        item = self._media_item_row(media_id)
        if item is None:
            return False
        if str(item.content_hash) != content_hash:
            return False

        key = (media_id, content_hash)
        candidates = self._trash_index.get(key, [])
        if not candidates:
            # Fallback: try filesystem scan
            self._scan_trash_folder()
            candidates = self._trash_index.get(key, [])
            if not candidates:
                return False
        # Pick first (earliest expiry)
        _expiry, src = candidates.pop(0)
        dst = self._resolve_disk_path_for_media_id(media_id)
        if dst is None:
            return False
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            return False
        if not src.exists():
            return False
        src.rename(dst)
        self._store_known_hash(dst, content_hash)
        self._upsert_media_item(media_id, str(item.rel_path), content_hash, trashed=0)
        return True

    def clean_trash(self) -> int:
        """Delete expired files currently in trash. Returns count removed."""
        now = int(time.time())
        removed = 0
        for entry in list(self.trash_dir.iterdir()):
            if not entry.is_file():
                continue
            _, _, expiry = parse_trash_stem(entry.stem)
            if expiry and expiry < now:
                try:
                    entry.unlink()
                    removed += 1
                except Exception:
                    pass
        # Refresh index
        self._scan_trash_folder()
        return removed
