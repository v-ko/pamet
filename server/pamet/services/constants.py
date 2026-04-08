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

# Length of hex digest to use for content hashes
# 32 hex chars = 128 bits (first half of SHA-256)
CONTENT_HASH_HEX_LEN = 32

# Maximum number of filesystem entries (dirs + files) to visit when walking
# a project folder.  Prevents runaway traversal if the user accidentally opens
# a huge directory (home folder, ML dataset, etc.).
MAX_WALK_ENTRIES = 50_000

# TODO: estimate this better
# Maximum size (in bytes) of a single .canvas file we're willing to parse.
# Anything larger is likely corrupt or not a real canvas file.
MAX_CANVAS_FILE_BYTES = 50 * 1024 * 1024  # 50 MB
