"""
V4 to V5 migration for Pamet pages (.pam4.json -> .pam5.json).

Handles: composite ID flattening, color role conversion, note type unification,
image metadata restructuring, internal URL rewrite, arrow endpoint restructuring.

After page conversion, a second pass creates ImageItem entity dicts for notes
that reference images (content.image) and rewrites them to use content.image_id.
The ImageItem dicts are written to project.pamet.json.

The element migration logic mirrors the TypeScript tmpDynamicMigration in
web-app/src/storage/DesktopImporter.ts.
"""

import copy
import hashlib
import json
import mimetypes
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fusion.logging import get_logger
from fusion.util import get_new_id
from pamet.storage.migrations.utils import backup_file

from ..file_system.color_roles import legacy_normalized_rgba_to_role

log = get_logger(__name__)

V4_FILE_EXT = ".pam4.json"
V5_FILE_EXT = ".pam5.json"

DEFAULT_TEXT_COLOR_ROLE = "onPrimary"
DEFAULT_BACKGROUND_COLOR_ROLE = "primary"

NOTE_LEGACY_TYPES = {
    "TextNote",
    "ImageNote",
    "ScriptNote",
    "CardNote",
    "OtherPageListNote",
}

# SHA-256 truncation length for content hashes (matches TS/constants.py)
_CONTENT_HASH_HEX_LEN = 32

PROJECT_CONFIG_FILENAME = "project.pamet.json"


def is_v4_page_file(path: Path) -> bool:
    """Check if the path is a V4 page file that needs migration to V5."""
    return path.is_file() and path.name.endswith(V4_FILE_EXT)


def _color_to_role(rgba_list) -> str:
    """Convert a V4 normalized RGBA list to a color role string."""
    rgba = list(rgba_list[:4])
    if len(rgba) == 3:
        rgba.append(1.0)
    return legacy_normalized_rgba_to_role(rgba)


def convert_v4_to_v5_element(
    element_data: Dict[str, Any], page_id: str
) -> Dict[str, Any]:
    """Convert a single V4 element dict to V5 format.

    Handles notes (all legacy types -> CardNote) and arrows.
    """
    if not isinstance(element_data, dict):
        return element_data

    original_type = element_data.get("type_name")

    # --- Flatten composite ID to "pageId-ownId" ---
    if isinstance(element_data.get("id"), list) and len(element_data["id"]) == 2:
        old_page_id, own_id = element_data["id"]
        element_data["id"] = f"{old_page_id}-{own_id}"
        element_data["parent_id"] = old_page_id
    else:
        element_data["parent_id"] = page_id

    # --- Ensure style/content/metadata exist ---
    style = element_data.get("style") or {}
    content = element_data.get("content") or {}
    metadata = element_data.get("metadata") or {}

    # --- Notes ---
    if original_type in NOTE_LEGACY_TYPES:
        # Convert colors to roles (or fill defaults)
        if isinstance(style.get("color"), list):
            style["color_role"] = _color_to_role(style.pop("color"))
        else:
            style.pop("color", None)
            style.setdefault("color_role", DEFAULT_TEXT_COLOR_ROLE)

        if isinstance(style.get("background_color"), list):
            style["background_color_role"] = _color_to_role(
                style.pop("background_color")
            )
        else:
            style.pop("background_color", None)
            style.setdefault("background_color_role", DEFAULT_BACKGROUND_COLOR_ROLE)

        if isinstance(style.get("border_color"), list):
            style["border_color_role"] = _color_to_role(style.pop("border_color"))
        else:
            style.pop("border_color", None)

        # Remove tags from root
        element_data.pop("tags", None)

        # Unify type to CardNote
        element_data["type_name"] = "CardNote"

        # OtherPageListNote -> project index header
        if original_type == "OtherPageListNote":
            metadata["is_project_index_header"] = True
            content.setdefault(
                "text",
                "Project links index (double-click to generate missing "
                "links, for e.g. new pages)",
            )
            style["color_role"] = "onSurface"
            style["background_color_role"] = "surfaceDim"

        # Internal link URL rewrite
        url = content.get("url")
        if isinstance(url, str) and url.startswith("pamet:/p"):
            content["url"] = url.replace("pamet:/p", "project:/page")

        # Image metadata migration
        image_size = metadata.pop("image_size", None)
        metadata.pop("image_md5", None)
        local_image_url = content.pop("local_image_url", None)
        if local_image_url:
            width, height = 0, 0
            if (
                isinstance(image_size, list)
                and len(image_size) >= 2
                and all(isinstance(v, (int, float)) for v in image_size[:2])
            ):
                width, height = image_size[:2]
            if local_image_url.startswith("pamet:/p"):
                image_url = local_image_url.replace("pamet:/p", "project:/p")
            else:
                image_url = f"project:/desktop/fs{local_image_url}"
            content["image"] = {"url": image_url, "width": width, "height": height}
        content.pop("image_url", None)  # remove redundant legacy field

    # --- Arrows ---
    elif original_type == "Arrow":
        # Prefix anchor note IDs with page_id (V4 stores own_id only)
        for key in ("tail_note_id", "head_note_id"):
            note_id = element_data.get(key)
            if note_id:
                element_data[key] = f"{page_id}-{note_id}"

        # Build structured endpoints
        element_data["tail"] = {
            "position": element_data.get("tail_coords"),
            "noteAnchorId": element_data.get("tail_note_id"),
            "noteAnchorType": (element_data.get("tail_anchor", "none").lower()),
        }
        element_data["head"] = {
            "position": element_data.get("head_coords"),
            "noteAnchorId": element_data.get("head_note_id"),
            "noteAnchorType": (element_data.get("head_anchor", "none").lower()),
        }

        # Mid points
        element_data["mid_points"] = [
            [c[0], c[1]]
            for c in element_data.get("mid_point_coords", [])
            if isinstance(c, list) and len(c) >= 2
        ]

        # Color role from root-level color
        base_color = element_data.get("color")
        if isinstance(base_color, list) and len(base_color) >= 3:
            style["color_role"] = _color_to_role(base_color)
        else:
            style.setdefault("color_role", DEFAULT_TEXT_COLOR_ROLE)

        # Arrow style properties (with defaults for null V4 values)
        style["line_type"] = element_data.get("line_type") or "solid"
        style["thickness"] = element_data.get("line_thickness") or 1
        style["line_function"] = (
            element_data.get("line_function_name") or "bezier_cubic"
        )
        style["head_shape"] = element_data.get("head_shape") or "arrow"
        style["tail_shape"] = element_data.get("tail_shape") or "arrow"

        # Remove all legacy arrow fields
        for field in (
            "tail_coords",
            "head_coords",
            "tail_note_id",
            "head_note_id",
            "tail_anchor",
            "head_anchor",
            "mid_point_coords",
            "color",
            "line_type",
            "line_thickness",
            "line_function_name",
            "head_shape",
            "tail_shape",
        ):
            element_data.pop(field, None)

    element_data["style"] = style
    element_data["content"] = content
    element_data["metadata"] = metadata
    return element_data


# ---------------------------------------------------------------------------
# Image → ImageItem migration helpers (no model dependency — plain dicts)
# ---------------------------------------------------------------------------


def _resolve_image_url(image_url: str, repo_path: Path) -> Optional[Path]:
    """Resolve a V5 content.image.url to an absolute file path.

    Handles any ``project:/...`` URL by treating the part after ``project:/``
    as a path relative to *repo_path*.

    Returns the absolute path or None for unrecognised/skipped URLs
    (e.g. http(s)).
    """
    if image_url.startswith("project:/"):
        rel = image_url[len("project:/") :]
        return repo_path / rel

    # http(s) or unknown — skip
    return None


def _compute_content_hash(file_path: Path) -> str:
    """SHA-256 of file contents, truncated to _CONTENT_HASH_HEX_LEN hex chars."""
    h = hashlib.sha256(file_path.read_bytes()).hexdigest()
    return h[:_CONTENT_HASH_HEX_LEN]


def _get_image_dimensions(file_path: Path) -> Tuple[int, int]:
    """Return (width, height) using Pillow.  Falls back to (0, 0)."""
    try:
        from PIL import Image

        with Image.open(file_path) as img:
            return img.size  # (width, height)
    except Exception as exc:
        log.warning(f"Could not read image dimensions from {file_path}: {exc}")
        return 0, 0


def _guess_mime(file_path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(file_path))
    return mime or "application/octet-stream"


def _build_image_item_dict(
    *,
    file_path: Path,
    rel_path: str,
    project_id: str,
    width: int,
    height: int,
) -> Dict[str, Any]:
    """Build a plain dict matching the ImageItem entity schema."""
    content_hash = _compute_content_hash(file_path)
    size = file_path.stat().st_size
    mime = _guess_mime(file_path)

    return {
        "id": get_new_id(),
        "parent_id": project_id,
        "type_name": "ImageItem",
        "path": rel_path,
        "content": {"hash": content_hash},
        "metadata": {
            "width": int(width),
            "height": int(height),
            "size": size,
            "mimeType": mime,
        },
    }


def migrate_image_notes(
    repo_path: Path,
    v5_page_paths: List[Path],
    project_id: str = "",
) -> List[Dict[str, Any]]:
    """Second pass over V5 pages: create ImageItem dicts and rewrite notes.

    For each note with ``content.image``:
    - Resolve the URL to a file on disk.
    - If the file exists: compute hash, get dimensions, build an ImageItem dict,
      replace ``content.image`` with ``content.image_id``.
    - If external: copy the file into ``<repo>/images/``.
    - If not found: set ``content.text`` to an error message, log warning.

    Returns a list of ImageItem plain dicts (for writing to project.pamet.json).
    """
    repo_path = Path(repo_path)
    image_items: List[Dict[str, Any]] = []

    for v5_path in v5_page_paths:
        try:
            with open(v5_path, "r", encoding="utf-8") as f:
                page_data = json.load(f)
        except Exception as exc:
            log.error(f"migrate_image_notes: failed to read {v5_path}: {exc}")
            continue

        modified = False

        for note in page_data.get("notes", []):
            content = note.get("content")
            if not content or not isinstance(content.get("image"), dict):
                continue

            image_info = content["image"]
            image_url = image_info.get("url", "")
            v4_width = image_info.get("width", 0)
            v4_height = image_info.get("height", 0)

            # Skip external web URLs
            if image_url.startswith("http://") or image_url.startswith("https://"):
                log.info(
                    f"  note {note['id']}: external web URL, "
                    f"keeping content.image as-is: {image_url}"
                )
                continue

            file_path = _resolve_image_url(image_url, repo_path)

            if file_path is None:
                log.warning(
                    f"  note {note['id']}: unrecognised image URL scheme: {image_url}"
                )
                continue

            if not file_path.exists():
                log.warning(
                    f"  note {note['id']}: image file not found: {file_path} "
                    f"(url: {image_url})"
                )
                content.pop("image", None)
                error_text = f"[Image not found at migration time: {image_url}]"
                if content.get("text"):
                    content["text"] += "\n" + error_text
                else:
                    content["text"] = error_text
                modified = True
                continue

            rel_path = str(file_path.relative_to(repo_path))

            # Get real dimensions (prefer Pillow, fall back to V4 metadata)
            pil_w, pil_h = _get_image_dimensions(file_path)
            width = pil_w if pil_w > 0 else int(v4_width)
            height = pil_h if pil_h > 0 else int(v4_height)

            item_dict = _build_image_item_dict(
                file_path=file_path,
                rel_path=rel_path,
                project_id=project_id,
                width=width,
                height=height,
            )
            image_items.append(item_dict)

            # Rewrite the note
            content.pop("image", None)
            content["image_id"] = item_dict["id"]
            modified = True

            log.info(
                f"  note {note['id']}: created ImageItem {item_dict['id']} "
                f"-> {rel_path}"
            )

        if modified:
            with open(v5_path, "w", encoding="utf-8") as f:
                json.dump(page_data, f, indent=2, ensure_ascii=False)

    return image_items


def convert_v4_to_v5_page_dict(page_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a v4 page dict to v5. Deep-copies to avoid mutating the input."""
    result = copy.deepcopy(page_data)

    page_id = result.get("id")
    if not page_id:
        raise ValueError("Page missing 'id'")

    if "children" in result:
        result["children"] = [
            convert_v4_to_v5_element(ch, page_id) for ch in result["children"]
        ]
    else:
        result["notes"] = [
            convert_v4_to_v5_element(n, page_id) for n in result.get("notes", [])
        ]
        result["arrows"] = [
            convert_v4_to_v5_element(a, page_id) for a in result.get("arrows", [])
        ]
    return result


def convert_v4_page_file(v4_file_path: Path, v5_file_path: Path) -> Path:
    """Convert a single .pam4.json file to .pam5.json."""
    with open(v4_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data = convert_v4_to_v5_page_dict(data)
    with open(v5_file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return v5_file_path


def migrate_v4_to_v5(repo_path: Path) -> List[Path]:
    """Convert all .pam4.json files in repo_path to .pam5.json.

    For each V4 page file:
      1. Convert to V5 format
      2. Back up the original into __migration_backup_v4_to_v5__/
      3. Remove the original .pam4.json

    Returns list of created .pam5.json paths.
    """
    repo_path = Path(repo_path)
    v4_backup_folder = repo_path / "__migration_backup_v4_to_v5__"

    v4_pages = [
        f for f in repo_path.iterdir() if f.is_file() and f.name.endswith(V4_FILE_EXT)
    ]

    if not v4_pages:
        return []

    log.info(f"migrate_v4_to_v5: converting {len(v4_pages)} page(s) in {repo_path}")
    converted = []

    for v4_path in v4_pages:
        try:
            with open(v4_path, "r", encoding="utf-8") as f:
                page_data = json.load(f)
            page_id = page_data["id"]

            v5_path = v4_path.parent / (page_id + V5_FILE_EXT)
            v5_data = convert_v4_to_v5_page_dict(page_data)

            with open(v5_path, "w", encoding="utf-8") as f:
                json.dump(v5_data, f, indent=2, ensure_ascii=False)

            backup_file(v4_path, v4_backup_folder)
            v4_path.unlink()
            log.info(f"  {v4_path.name} -> {v5_path.name}")
            converted.append(v5_path)

        except Exception as e:
            log.error(f"  FAILED to convert {v4_path.name}: {e}")
            continue

    log.info(f"migrate_v4_to_v5: done, {len(converted)}/{len(v4_pages)} converted")

    # Second pass: create ImageItem dicts from notes with content.image
    if converted:
        image_items = migrate_image_notes(repo_path, converted)
        if image_items:
            project_config_path = repo_path / PROJECT_CONFIG_FILENAME
            # Load existing config or start fresh
            if project_config_path.exists():
                with open(project_config_path, "r", encoding="utf-8") as f:
                    project_config = json.load(f)
            else:
                project_config = {}

            existing = project_config.get("image_items", [])
            existing.extend(image_items)
            project_config["image_items"] = existing

            with open(project_config_path, "w", encoding="utf-8") as f:
                json.dump(project_config, f, indent=2, ensure_ascii=False)

            log.info(
                f"migrate_v4_to_v5: wrote {len(image_items)} ImageItem(s) "
                f"to {project_config_path.name}"
            )

    return converted
