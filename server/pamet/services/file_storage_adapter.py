from __future__ import annotations

import hashlib
import time
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Dict, Optional, Tuple

from fusion.logging import get_logger

from pamet.services.constants import CONTENT_HASH_HEX_LEN, DEFAULT_TRASH_RETENTION_S
from pamet.services.media_utils import build_trash_filename, parse_trash_stem

if TYPE_CHECKING:
    from pamet.services.project_sync.project_folder_manager import ProjectFolderManager

log = get_logger(__name__)

# No FastAPI dependencies here; this is a pure service


class FileStorageAdapter:
    """
    Desktop media backend that stores files directly in the project folder.

    Files are addressed by ``FileItem.path`` (relative to the project root).
    Path lookups use the PFM in-memory entity store — no local DB.

    NOTE: A file-stat index DB (for detecting offline media changes) is
    deferred.  When implemented it should live under ``.pamet/`` and be
    created lazily.
    """

    TRASH_DIR = "media-backup"

    def __init__(
        self,
        repo_root: Path,
        project_manager: "ProjectFolderManager | None" = None,
    ):
        self.repo_root = Path(repo_root)
        self.project_manager = project_manager
        self.pamet_dir = self.repo_root / ".pamet"
        self.pamet_dir.mkdir(parents=True, exist_ok=True)
        self.trash_dir = self.pamet_dir / self.TRASH_DIR
        self._trash_index: Dict[Tuple[str, str], list[Tuple[int, Path]]] = {}
        self._scan_trash_folder()

    # -- path helpers --------------------------------------------------------

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

    def _resolve_path_for_media_id(self, media_id: str) -> Path | None:
        """Look up rel_path for *media_id* from the PFM entity store."""
        if self.project_manager is None:
            return None
        entity = self.project_manager._entity_store.get(media_id)
        if entity is None:
            return None
        rel_path = entity.get("path")
        if not isinstance(rel_path, str) or not rel_path:
            return None
        try:
            return self._resolve_relative_path(rel_path)
        except ValueError:
            return None

    # -- hashing -------------------------------------------------------------

    @staticmethod
    def compute_content_hash(path: Path) -> str:
        """SHA-256 of file contents, truncated to CONTENT_HASH_HEX_LEN."""
        data = path.read_bytes()
        return hashlib.sha256(data).hexdigest()[:CONTENT_HASH_HEX_LEN]

    # ----- Trash helpers -----

    def _scan_trash_folder(self):
        self._trash_index.clear()
        if not self.trash_dir.exists():
            return
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

    def _move_existing_path_to_trash(
        self,
        src: Path,
        media_id: str,
        content_hash: str,
        retention_s: int | None = None,
    ) -> bool:
        if not src.exists():
            return False

        self.trash_dir.mkdir(parents=True, exist_ok=True)
        expiry = int(time.time()) + int(retention_s or DEFAULT_TRASH_RETENTION_S)
        dst = self.trash_dir / build_trash_filename(
            media_id, content_hash, expiry, src.suffix
        )
        src.rename(dst)
        key = (media_id, content_hash)
        self._trash_index.setdefault(key, []).append((expiry, dst))
        self._trash_index[key].sort(key=lambda t: t[0])
        return True

    # --- High-level operations used by the API layer ---

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
            current_hash = self.compute_content_hash(dest)
            if current_hash != content_hash:
                self._move_existing_path_to_trash(dest, media_id, current_hash)

        dest.write_bytes(data)

    def find_item_path(self, media_id: str, content_hash: str) -> Path | None:
        """Resolve the active file path for an item, validating its current hash."""
        path = self._resolve_path_for_media_id(media_id)
        if path is None or not path.exists():
            return None

        current_hash = self.compute_content_hash(path)
        if current_hash != content_hash:
            return None
        return path

    def move_to_trash(
        self, media_id: str, content_hash: str, retention_s: int | None = None
    ) -> bool:
        """Move the current file version to the trash backup folder."""
        src = self.find_item_path(media_id, content_hash)
        if src is None:
            return False
        return self._move_existing_path_to_trash(
            src, media_id, content_hash, retention_s
        )

    def restore_from_trash(self, media_id: str, content_hash: str) -> bool:
        """Restore an item from trash to its active path. Returns True if restored."""
        dst = self._resolve_path_for_media_id(media_id)
        if dst is None:
            return False

        key = (media_id, content_hash)
        candidates = self._trash_index.get(key, [])
        if not candidates:
            self._scan_trash_folder()
            candidates = self._trash_index.get(key, [])
            if not candidates:
                return False
        # Pick first (earliest expiry)
        _expiry, src = candidates.pop(0)
        if not src.exists():
            return False
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            return False
        src.rename(dst)
        return True

    def clean_trash(self) -> int:
        """Delete expired files currently in trash. Returns count removed."""
        if not self.trash_dir.exists():
            return 0
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
