from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Tuple
import hashlib
import time

from pamet.services.constants import CONTENT_HASH_HEX_LEN, DEFAULT_TRASH_RETENTION_S, ALLOWED_MEDIA_EXTENSIONS
from pamet.services.media_utils import ext_from_mime, parse_trash_stem, build_trash_filename
from peewee import Model, TextField, IntegerField, SqliteDatabase

# No FastAPI dependencies here; this is a pure service


@dataclass
class MediaStorageBackendService:
    """
    Simple media backend for the desktop app.

    Stores blobs on disk under a stable id#hash filename. Routing is provided
    via an external APIRouter created by create_media_router().
    """
    media_root: Path
    project_manager: object | None = None  # ProjectFolderManager (for future use)

    # Folder names
    ITEMS_DIR: str = "__items__"
    # Trash now lives under repo/.pamet/media-backup
    TRASH_DIR: str = "media-backup"

    def __post_init__(self):
        self.media_root = Path(self.media_root)
        (self.media_root / self.ITEMS_DIR).mkdir(parents=True, exist_ok=True)

        # Database under .pamet/media.db
        # Infer repo root from media_root parent
        self.repo_root = self.media_root.parent
        self.pamet_dir = self.repo_root / '.pamet'
        self.pamet_dir.mkdir(parents=True, exist_ok=True)
        self.trash_dir = self.pamet_dir / self.TRASH_DIR
        self.trash_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Peewee database for media cache
        self._db = SqliteDatabase(str(self.pamet_dir / 'media.db'))
        self._init_db()

        # Runtime indices for trashed items: (id, hash) -> list[(expiry_ts, path)]
        self._trash_index: Dict[Tuple[str, str], list[Tuple[int, Path]]] = {}
        self._scan_trash_folder()

    def _item_path(self, media_id: str, content_hash: str, ext: str = "") -> Path:
        filename = f"{media_id}#{content_hash}{ext}"
        return self.media_root / self.ITEMS_DIR / filename

    def _trash_path(self, media_id: str, content_hash: str, ext: str = "") -> Path:
        filename = f"{media_id}#{content_hash}{ext}"
        return self.trash_dir / filename

    # ----- DB helpers -----
    def _init_db(self):
        class BaseModel(Model):
            class Meta:
                database = self._db

        class MediaCache(BaseModel):
            path = TextField(unique=True)
            mtime = IntegerField()
            hash = TextField()

        # Bind models to instance for later access
        self.MediaCache = MediaCache

        with self._db.bind_ctx([MediaCache]):
            self._db.create_tables([MediaCache])

    def compute_and_cache_hash(self, path: Path) -> str:
        data = path.read_bytes()
        full = hashlib.sha256(data).hexdigest()
        short = full[:CONTENT_HASH_HEX_LEN]
        mtime = int(path.stat().st_mtime)
        # Upsert behavior: try fetch; if present -> update; else create
        with self._db.atomic():
            rec = self.MediaCache.get_or_none(self.MediaCache.path == str(path))
            if rec is None:
                self.MediaCache.create(path=str(path), mtime=mtime, hash=short)
            else:
                rec.mtime = mtime
                rec.hash = short
                rec.save()
        return short

    def get_cached_hash(self, path: Path) -> Optional[str]:
        mtime = int(path.stat().st_mtime)
        rec = self.MediaCache.get_or_none(self.MediaCache.path == str(path))
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
    def save_bytes(self, media_id: str, content_hash: str, data: bytes, mime_type: Optional[str]) -> None:
        """Persist a media blob under id+hash, guessing extension from mime."""
        ext = ext_from_mime(mime_type)
        dest = self._item_path(media_id, content_hash, ext)
        dest.write_bytes(data)

    def find_item_path(self, media_id: str, content_hash: str) -> Path | None:
        """Return an existing path for an item if present, trying known extensions."""
        # Try empty ext first, then all allowed extensions
        candidates = [self._item_path(media_id, content_hash)]
        candidates += [self._item_path(media_id, content_hash, ext) for ext in ALLOWED_MEDIA_EXTENSIONS]
        for p in candidates:
            if p.exists():
                return p
        return None

    def move_to_trash(self, media_id: str, content_hash: str, retention_s: int | None = None) -> bool:
        """Move an existing item to trash backup folder with expiry in name.

        Name format: id-hash-expiry_unix_time_seconds.ext
        Returns True if moved.
        """
        for ext in [""] + sorted(ALLOWED_MEDIA_EXTENSIONS):
            src = self._item_path(media_id, content_hash, ext)
            if src.exists():
                expiry = int(time.time()) + int(retention_s or DEFAULT_TRASH_RETENTION_S)
                dst = self.trash_dir / build_trash_filename(media_id, content_hash, expiry, src.suffix)
                src.rename(dst)
                key = (media_id, content_hash)
                self._trash_index.setdefault(key, []).append((expiry, dst))
                self._trash_index[key].sort(key=lambda t: t[0])
                return True
        return False

    def restore_from_trash(self, media_id: str, content_hash: str) -> bool:
        """Restore an item from trash to items. Returns True if restored."""
        key = (media_id, content_hash)
        candidates = self._trash_index.get(key, [])
        if not candidates:
            # Fallback: try filesystem scan
            self._scan_trash_folder()
            candidates = self._trash_index.get(key, [])
            if not candidates:
                return False
        # Pick first (earliest expiry)
        expiry, src = candidates.pop(0)
        dst = self._item_path(media_id, content_hash, src.suffix)
        if not src.exists():
            return False
        src.rename(dst)
        return True

    def clean_trash(self) -> int:
        """Delete expired files currently in trash. Returns count removed."""
        now = int(time.time())
        removed = 0
        for entry in list(self.trash_dir.iterdir()):
            if not entry.is_file():
                continue
            stem = entry.stem
            expiry = 0
            if '-' in stem:
                parts = stem.split('-')
                if len(parts) >= 3:
                    try:
                        expiry = int(parts[2])
                    except Exception:
                        expiry = 0
            if expiry and expiry < now:
                try:
                    entry.unlink()
                    removed += 1
                except Exception:
                    pass
        # Refresh index
        self._scan_trash_folder()
        return removed
