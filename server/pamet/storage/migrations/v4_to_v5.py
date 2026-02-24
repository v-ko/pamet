"""
V4 to V5 migration for Pamet pages (.pam4.json -> .pam5.json).

Handles: composite ID flattening, color role conversion, note type unification,
image metadata restructuring, internal URL rewrite, arrow endpoint restructuring.

The element migration logic mirrors the TypeScript tmpDynamicMigration in
web-app/src/storage/DesktopImporter.ts.
"""

import copy
import json
from pathlib import Path
from typing import Any, Dict, List

from fusion.logging import get_logger
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
    return converted
