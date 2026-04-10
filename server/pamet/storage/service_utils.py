from __future__ import annotations

from pathlib import Path

from fusion.libs.entity import Entity, load_from_dict

from pamet.services.constants import MAX_CANVAS_FILE_BYTES
from pamet.storage.canvas_html import read_canvas_file as _read_canvas_html


class ForeignCanvasFile(Exception):
    """Raised when a .canvas file has a different schema (not a pamet file)."""


class CanvasParseError(Exception):
    """Raised when a pamet .canvas file cannot be parsed due to an unexpected error."""


class ProjectTooLargeError(Exception):
    """Raised when a project folder exceeds the walk budget."""


def read_canvas_file(canvas_path: Path, repo_root: Path) -> dict[str, Entity]:
    """Parse a .canvas file and return a flat {entity_id → Entity} map.

    The Page entity's ``path`` is inferred from the file's location relative
    to *repo_root* (any serialized ``path`` or legacy ``name`` is ignored).

    Raises ForeignCanvasFile if the file doesn't look like a pamet canvas
    (missing or wrong schema indicators — e.g. from Obsidian).
    Raises CanvasParseError on unexpected errors in an otherwise valid file.
    """
    try:
        file_size = canvas_path.stat().st_size
        if file_size > MAX_CANVAS_FILE_BYTES:
            raise CanvasParseError(
                f"Canvas file {canvas_path} is {file_size} bytes, "
                f"exceeds limit of {MAX_CANVAS_FILE_BYTES}"
            )
        page_data = _read_canvas_html(canvas_path)
    except (CanvasParseError, ForeignCanvasFile):
        raise
    except Exception as exc:
        raise CanvasParseError(f"Failed to read canvas file {canvas_path}") from exc

    if not isinstance(page_data, dict):
        raise ForeignCanvasFile(
            f"Canvas file {canvas_path}: top-level value is not a JSON object"
        )

    # Schema check: a pamet canvas file must have type_name == "Page"
    type_name = page_data.get("type_name")
    if type_name != "Page":
        raise ForeignCanvasFile(
            f"Canvas file {canvas_path}: type_name is {type_name!r}, expected 'Page'"
        )

    page_id = page_data.get("id")
    if not page_id:
        raise CanvasParseError(f"Canvas file {canvas_path} has no 'id' field")

    notes = page_data.pop("notes", [])
    arrows = page_data.pop("arrows", [])
    file_items = page_data.pop("file_items", [])

    # Infer path from file location, strip any serialized path/name
    page_data.pop("path", None)
    page_data.pop("name", None)
    page_data["path"] = canvas_path.relative_to(repo_root).as_posix()

    entities: dict[str, Entity] = {}

    # Page entity
    entities[page_id] = load_from_dict(page_data)

    for child_dict in (*notes, *arrows, *file_items):
        child_id = child_dict.get("id")
        if child_id:
            entities[child_id] = load_from_dict(child_dict)

    return entities
