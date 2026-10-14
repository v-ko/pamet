from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from sivkit.libs.model import Entity, load_from_dict

from pamet.services.constants import MAX_CANVAS_FILE_BYTES
from pamet.storage.canvas_html import read_canvas_file as _read_canvas_html


class ForeignCanvasFile(Exception):
    """Raised when a .canvas file has a different schema (not a pamet file)."""


class CanvasParseError(Exception):
    """Raised when a pamet .canvas file cannot be parsed due to an unexpected error."""


class ProjectTooLargeError(Exception):
    """Raised when a project folder exceeds the walk budget."""


@dataclass(frozen=True)
class ProjectProblem:
    """A problem with a project's files, listed in ``/status`` until cleared."""

    kind: Literal["unreadable_file", "unlisted_folder"]
    path: str  # Relative to the project root
    reason: str


def read_canvas_file(canvas_path: Path, repo_root: Path) -> dict[str, Entity]:
    """Parse a .canvas file and return a flat {entity_id → Entity} map.

    The Page entity's ``path`` is inferred from the file's location relative
    to *repo_root* (any serialized ``path`` or legacy ``name`` is ignored).

    Raises ForeignCanvasFile if the file doesn't look like a pamet canvas
    (missing or wrong schema indicators — e.g. from Obsidian).
    Raises CanvasParseError on any other failure, from reading the file to
    building its entities, so a broken file never fails the caller's scan.
    """
    try:
        file_size = canvas_path.stat().st_size
        if file_size > MAX_CANVAS_FILE_BYTES:
            raise CanvasParseError(
                f"{file_size} bytes exceeds the limit of {MAX_CANVAS_FILE_BYTES}"
            )
        page_data = _read_canvas_html(canvas_path)

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
            raise CanvasParseError("The page has no 'id' field")

        notes = page_data.pop("notes", [])
        arrows = page_data.pop("arrows", [])

        # Infer path from file location, strip any serialized path/name
        page_data.pop("path", None)
        page_data.pop("name", None)
        page_data["path"] = canvas_path.relative_to(repo_root).as_posix()

        entities: dict[str, Entity] = {}

        # Page entity
        entities[page_id] = load_from_dict(page_data)

        for child_dict in (*notes, *arrows):
            child_id = child_dict.get("id")
            if child_id:
                entities[child_id] = load_from_dict(child_dict)

        return entities
    except (CanvasParseError, ForeignCanvasFile):
        raise
    except Exception as exc:
        raise CanvasParseError(f"{type(exc).__name__}: {exc}") from exc
