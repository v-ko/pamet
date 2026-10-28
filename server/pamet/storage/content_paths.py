"""Pamet content boundaries, separate from discovery exclusions."""

from sivkit.storage.fs.names import canonical_key
from sivkit.storage.fs.ops import UnsafePath

from pamet.services.constants import CANVAS_FILE_EXT


def is_metadata_path(rel: str) -> bool:
    return any(canonical_key(part) == ".pamet" for part in rel.split("/"))


def check_media_path(rel: str) -> None:
    """Keep internal state and pages out of attachment operations."""
    if is_metadata_path(rel):
        raise UnsafePath(rel, "Pamet metadata")
    if canonical_key(rel).endswith(CANVAS_FILE_EXT):
        raise UnsafePath(rel, "canvas file")
