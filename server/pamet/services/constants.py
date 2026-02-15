from __future__ import annotations

# Media-related constants (server-side)

# MIME type to extension mapping (normalized to lowercase)
MIME_TO_EXT = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/bmp": ".bmp",
    "image/tiff": ".tiff",
    "image/svg+xml": ".svg",
}

# Allowed media extensions for indexing and lookup are derived from the mapping
# Normalized to lowercase with leading dot
ALLOWED_MEDIA_EXTENSIONS = set(MIME_TO_EXT.values()) | {".jpeg", ".tif"}

# Default trash retention in seconds (7 days)
DEFAULT_TRASH_RETENTION_S = 7 * 24 * 60 * 60

# Length of hex digest to use for content hashes
# 32 hex chars = 128 bits (first half of SHA-256)
CONTENT_HASH_HEX_LEN = 32
