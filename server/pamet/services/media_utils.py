from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple
from pamet.services.constants import MIME_TO_EXT


def ext_from_mime(mime_type: Optional[str]) -> str:
    if not mime_type:
        return ""
    return MIME_TO_EXT.get(mime_type.lower(), "")


def parse_trash_stem(stem: str) -> Tuple[Optional[str], Optional[str], int]:
    """Parse a trash file stem into (id, hash, expiry_unix_ts) if possible.

    Supports legacy variant with 'id#hash'.
    """
    media_id: Optional[str] = None
    content_hash: Optional[str] = None
    expiry = 0
    if '-' in stem:
        parts = stem.split('-')
        if len(parts) >= 3:
            media_id, content_hash, exp_str = parts[0], parts[1], parts[2]
            try:
                expiry = int(exp_str)
            except Exception:
                expiry = 0
    elif '#' in stem:
        try:
            media_id, content_hash = stem.split('#', 1)
        except ValueError:
            media_id, content_hash = None, None
    return media_id, content_hash, expiry


def build_trash_filename(media_id: str, content_hash: str, expiry_unix_s: int, suffix: str) -> str:
    return f"{media_id}-{content_hash}-{expiry_unix_s}{suffix}"
