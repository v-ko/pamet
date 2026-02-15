"""
V4 to V5 migration functionality for Pamet pages.

This module handles the conversion from .pam4.json to .pam5.json format,
including color role conversion, composite ID flattening, note type unification,
and other format changes.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

from fusion.logging import get_logger
from pamet.storage.migrations.utils import backup_file

from ..file_system.color_roles import (
    approximate_rgba_to_role,
    legacy_normalized_rgba_to_role,
)

log = get_logger(__name__)

"""Color role constants & old_color_to_role moved to color_roles module."""

V4_FILE_EXT = ".pam4.json"
V5_FILE_EXT = ".pam5.json"


def is_v4_page_file(path: Path) -> bool:
    """Check if the path is a V4 page file that needs migration to V5."""
    return path.is_file() and path.name.endswith(V4_FILE_EXT)


def _base_migrate_element(element_data: dict, page_id: str) -> dict:
    """Base migration step: ID flattening, note color roles, ensure content/metadata.

    This is a private helper called by convert_v4_to_v5_element.
    """

    # Convert composite ID to flat ID with parent_id
    if isinstance(element_data.get("id"), list) and len(element_data["id"]) == 2:
        old_page_id, own_id = element_data["id"]
        element_data["id"] = f"{old_page_id}-{own_id}"
        element_data["parent_id"] = old_page_id
    else:
        # Handle case where ID might already be converted or malformed
        element_data["parent_id"] = page_id

    # Initialize style if missing
    if "style" not in element_data:
        element_data["style"] = {}

    # Convert colors to roles for notes (type unification, content migration,
    # arrow restructuring are all handled by convert_v4_to_v5_element which
    # calls this function as a first step)
    if element_data.get("type_name") in [
        "TextNote",
        "ImageNote",
        "ScriptNote",
        "CardNote",
    ]:
        migrate_note_colors(element_data)
        migrate_note_metadata(element_data)

    # Ensure content and metadata exist
    if "content" not in element_data:
        element_data["content"] = {}
    if "metadata" not in element_data:
        element_data["metadata"] = {}

    return element_data


def migrate_note_colors(note_data: dict):
    """Convert note colors from RGBA floats (0..1) to color roles."""
    style = note_data.get("style", {})

    def _assign_role(src_key: str, dest_key: str):
        col = style.get(src_key)
        if not (isinstance(col, list) and len(col) >= 3):
            return

        rgba = list(col[:4])
        if len(rgba) == 3:
            rgba.append(1.0)  # Default alpha for normalized colors

        # V4 colors are always normalized floats
        style[dest_key] = legacy_normalized_rgba_to_role(rgba)

    _assign_role("background_color", "background_color_role")
    _assign_role("color", "color_role")
    _assign_role("border_color", "border_color_role")

    # Remove legacy raw RGBA arrays once roles assigned
    for legacy_key in ["background_color", "color", "border_color"]:
        if legacy_key in style:
            del style[legacy_key]
    note_data["style"] = style


def migrate_note_type(note_data: dict):
    """Unify all note types to 'Note'"""
    if note_data.get("type_name") in [
        "TextNote",
        "ImageNote",
        "ScriptNote",
        "CardNote",
    ]:
        note_data["type_name"] = "Note"


def migrate_note_content(note_data: dict, page_id: str):
    """Migrate note content structure"""
    content = note_data.get("content", {})

    # Handle image notes - migrate image metadata
    if "image" in content:
        image_data = content["image"]
        if isinstance(image_data, dict):
            # Ensure image has proper metadata structure
            if "metadata" not in image_data:
                image_data["metadata"] = {}

            # Convert any old image format to new format
            if "url" in image_data and not image_data["url"].startswith("data:"):
                # Convert relative URLs to proper format
                if not image_data["url"].startswith(("http://", "https://", "file://")):
                    image_data["url"] = f"file://{image_data['url']}"

    # Handle script notes - ensure proper structure
    if "script" in content:
        script_data = content["script"]
        if isinstance(script_data, str):
            # Convert string script to object format
            content["script"] = {
                "code": script_data,
                "language": "python",  # Default language
                "metadata": {},
            }

    # Handle text content - ensure it's properly structured
    if "text" in content and isinstance(content["text"], str):
        # Text content is already in the right format
        pass


def migrate_note_metadata(note_data: dict):
    """Migrate note metadata structure"""
    metadata = note_data.get("metadata", {})

    # Remove tags from the root of the note data if they exist
    if "tags" in note_data:
        del note_data["tags"]

    note_data["metadata"] = metadata


def migrate_arrow_format(arrow_data: dict, page_id: str):
    """Migrate arrow format and colors"""
    # Convert arrow colors
    migrate_arrow_colors(arrow_data)

    # Convert arrow endpoints if they have composite IDs
    if "tail_note_id" in arrow_data:
        tail_id = arrow_data["tail_note_id"]
        if isinstance(tail_id, list) and len(tail_id) == 2:
            arrow_data["tail_note_id"] = f"{tail_id[0]}-{tail_id[1]}"

    if "head_note_id" in arrow_data:
        head_id = arrow_data["head_note_id"]
        if isinstance(head_id, list) and len(head_id) == 2:
            arrow_data["head_note_id"] = f"{head_id[0]}-{head_id[1]}"

    # Ensure arrow has proper metadata
    if "metadata" not in arrow_data:
        arrow_data["metadata"] = {}


def migrate_arrow_colors(arrow_data: dict):
    """Convert arrow colors from RGBA floats to color roles"""
    style = arrow_data.get("style", {})

    def _assign_arrow_role(src_key: str, dest_key: str):
        col = style.get(src_key)
        if not (isinstance(col, list) and len(col) >= 3):
            return

        rgba = list(col[:4])
        if len(rgba) == 3:
            rgba.append(1.0)

        # V4 colors are always normalized floats
        style[dest_key] = legacy_normalized_rgba_to_role(rgba)

    _assign_arrow_role("line_color", "line_color_role")
    _assign_arrow_role("head_color", "head_color_role")
    _assign_arrow_role("color", "color_role")  # Handle legacy 'color' field

    # Remove legacy fields
    for legacy_key in ["line_color", "head_color", "color"]:
        if legacy_key in style:
            del style[legacy_key]

    arrow_data["style"] = style


# -------- Extended adaptation logic (factored out from MigrationManager) -------- #

NOTE_LEGACY_TYPES = [
    "TextNote",
    "ImageNote",
    "ScriptNote",
    "CardNote",
    "OtherPageListNote",
]


def _normalize_color_channels(style: dict):
    """Normalize only arrow line_color from 0..1 to 0..255 after migration."""
    for key in ["line_color"]:
        col = style.get(key)
        if (
            isinstance(col, list)
            and col
            and all(isinstance(c, (int, float)) for c in col)
        ):
            if max(col) <= 1.0:
                rgba = [int(round(c * 255)) for c in col[:4]]
                if len(rgba) == 3:
                    rgba.append(255)
                style[key] = rgba


def convert_v4_to_v5_element(
    element_data: Dict[str, Any], page_id: str
) -> Dict[str, Any]:
    """
    Single entry point for converting a V4 element dict to V5 format.

    Delegates to migrate_v4_to_v5_element for base conversion (ID flattening,
    note color role mapping) and then applies the remaining schema changes:
    CardNote type unification, image metadata, internal URL rewrite, arrow
    endpoint restructuring, etc.
    """
    if not isinstance(element_data, dict):
        return element_data

    original_type = element_data.get("type_name")
    style = element_data.get("style") or {}
    # Don't normalize note colors yet; we need raw values to choose mapping. Arrow
    # line colors are normalized later.
    if style:
        element_data["style"] = style

    # Delegate base migration (handles composite IDs, basic color roles)
    try:
        migrated = _base_migrate_element(element_data, page_id)
    except Exception as e:
        log.error(
            f'_base_migrate_element failed for element {element_data.get("id")}: {e}'
        )
        migrated = element_data

    # NOTE TYPE unification & special header
    if original_type in NOTE_LEGACY_TYPES:
        # Unify to CardNote if coming from legacy set
        if migrated.get("type_name") in ["Note", "TextNote", "ImageNote", "ScriptNote"]:
            migrated["type_name"] = "CardNote"
        if original_type == "OtherPageListNote":
            migrated.setdefault("metadata", {})
            migrated.setdefault("content", {})
            migrated.setdefault("style", {})
            migrated["metadata"]["is_project_index_header"] = True
            migrated["content"].setdefault(
                "text",
                "Project links index (double-click to generate missing links, for e.g. new pages)",
            )
            migrated["style"].setdefault("color_role", "onSurface")
            migrated["style"].setdefault("background_color_role", "surfaceDim")

    # Internal link URL rewrite
    content = migrated.get("content") or {}
    url = content.get("url")
    if isinstance(url, str) and url.startswith("pamet:/p"):
        content["url"] = url.replace("pamet:/p", "project:/page")
    migrated["content"] = content

    # Image metadata migration (if not already handled)
    metadata = migrated.get("metadata") or {}
    image_size = metadata.pop("image_size", None)
    metadata.pop("image_md5", None)
    local_image_url = content.get("local_image_url")
    if local_image_url:
        # Remove legacy field
        del content["local_image_url"]
        width = 0
        height = 0
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
    # Remove stray image_url field if present (redundant)
    if "image_url" in content:
        # Keep any already-created content['image'] but drop the old scalar field
        del content["image_url"]
    migrated["content"] = content
    migrated["metadata"] = metadata

    # Arrow extended conversion (endpoints + style) if still raw
    if (
        original_type == "Arrow" or migrated.get("type_name") == "Arrow"
    ) and "tail" not in migrated:
        # Anchor ID prefixing
        for anchor_key in ["tail_note_id", "head_note_id"]:
            if anchor_key in migrated and migrated[anchor_key]:
                if (
                    isinstance(migrated[anchor_key], list)
                    and len(migrated[anchor_key]) == 2
                ):
                    # Composite already flattened in base step, but if list, flatten
                    migrated[anchor_key] = (
                        f"{migrated[anchor_key][0]}-{migrated[anchor_key][1]}"
                    )
                elif (
                    isinstance(migrated[anchor_key], str)
                    and "-" not in migrated[anchor_key]
                ):
                    migrated[anchor_key] = f"{page_id}-{migrated[anchor_key]}"

        tail_coords = migrated.get("tail_coords") or migrated.get("tail_point")
        head_coords = migrated.get("head_coords") or migrated.get("head_point")
        tail_anchor = migrated.get("tail_anchor_type") or migrated.get("tail_anchor")
        head_anchor = migrated.get("head_anchor_type") or migrated.get("head_anchor")
        migrated["tail"] = {
            "position": tail_coords if tail_coords else None,
            "noteAnchorId": migrated.get("tail_note_id"),
            "noteAnchorType": (
                tail_anchor.lower() if isinstance(tail_anchor, str) else "none"
            ),
        }
        migrated["head"] = {
            "position": head_coords if head_coords else None,
            "noteAnchorId": migrated.get("head_note_id"),
            "noteAnchorType": (
                head_anchor.lower() if isinstance(head_anchor, str) else "none"
            ),
        }
        # Mid points
        mp_coords = migrated.get("mid_point_coords", [])
        new_mid_points = []
        for coords in mp_coords:
            if isinstance(coords, list) and len(coords) >= 2:
                new_mid_points.append([coords[0], coords[1]])
            else:
                log.warning(f"Invalid mid point coordinates: {coords}")
                new_mid_points.append([0, 0])
        migrated["mid_points"] = new_mid_points

        # Style mapping if not already replaced
        style = migrated.get("style") or {}
        base_color = migrated.get("color") or migrated.get("line_color")
        if base_color is not None and isinstance(base_color, list):
            if max(base_color) <= 1.0:
                base_color_norm = [int(round(c * 255)) for c in base_color[:4]]
                if len(base_color_norm) == 3:
                    base_color_norm.append(255)
                base_color = base_color_norm
        rgba_tuple = None
        if isinstance(base_color, list):
            tmp = base_color[:4]
            while len(tmp) < 4:
                tmp.append(255)
            rgba_tuple = (int(tmp[0]), int(tmp[1]), int(tmp[2]), int(tmp[3]))
        style.update(
            {
                "color_role": (
                    approximate_rgba_to_role(rgba_tuple)
                    if rgba_tuple
                    else style.get("color_role", "primary")
                ),
                "line_type": migrated.get("line_type", "solid"),
                "thickness": migrated.get("line_thickness", 1),
                "line_function": migrated.get("line_function_name", "bezier_cubic"),
                "head_shape": migrated.get("head_shape", "arrow"),
                "tail_shape": migrated.get("tail_shape", "arrow"),
            }
        )
        migrated["style"] = style
        # Remove legacy arrow fields
        for legacy_field in [
            "tail_coords",
            "head_coords",
            "tail_point",
            "head_point",
            "tail_note_id",
            "head_note_id",
            "tail_anchor",
            "head_anchor",
            "tail_anchor_type",
            "head_anchor_type",
            "mid_point_coords",
            "color",
            "line_color",
            "line_type",
            "line_thickness",
            "line_function_name",
            "head_shape",
            "tail_shape",
        ]:
            migrated.pop(legacy_field, None)

    migrated.setdefault("content", {})
    migrated.setdefault("metadata", {})
    migrated.setdefault("style", {})
    _normalize_color_channels(migrated.get("style", {}))
    return migrated


def migrate_v4_notes_and_arrows(
    notes: List[Dict[str, Any]], arrows: List[Dict[str, Any]], page_id: str
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Batch adapt notes and arrows using convert_v4_to_v5_element."""
    migrated_notes = [convert_v4_to_v5_element(n, page_id) for n in notes]
    migrated_arrows = [convert_v4_to_v5_element(a, page_id) for a in arrows]
    return migrated_notes, migrated_arrows


def convert_v4_to_v5_page_dict(page_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Accepts a v4 page dict (either with 'children' or 'notes'+'arrows') and
    returns a new v5 page dict (the original is not mutated).
    """
    import copy

    result = copy.deepcopy(page_data)

    page_id = result.get("id")
    if not page_id:
        raise Exception("Page missing ID")

    # If unified children format
    if "children" in result:
        result["children"] = [
            convert_v4_to_v5_element(ch, page_id) for ch in result.get("children", [])
        ]
    else:
        notes = result.get("notes", [])
        arrows = result.get("arrows", [])
        migrated_notes, migrated_arrows = migrate_v4_notes_and_arrows(
            notes, arrows, page_id
        )
        result["notes"] = migrated_notes
        result["arrows"] = migrated_arrows
    return result


def convert_v4_page_file(v4_file_path: Path, v5_file_path: Path):
    """High-level file conversion entry point using the factored migration."""
    with open(v4_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data = convert_v4_to_v5_page_dict(data)
    with open(v5_file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return v5_file_path


def retrofit_existing_v5_file(file_path: Path):
    """Retrofit an already-converted .pam5.json to remove legacy RGBA fields and add roles.

    Creates a .bak file the first time it modifies the page.
    """
    p = Path(file_path)
    with p.open("r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except Exception as e:
            log.error(f"Failed to load JSON for retrofit {p}: {e}")
            return p
    changed = False
    # page_id not needed for retrofit beyond potential future logging

    def _process(entity: Dict[str, Any]):
        nonlocal changed
        if not isinstance(entity, dict):
            return
        # Flatten composite id if still list
        if isinstance(entity.get("id"), list) and len(entity["id"]) == 2:
            old_pid, own = entity["id"]
            entity["id"] = f"{old_pid}-{own}"
            entity["parent_id"] = old_pid
            changed = True
        style = entity.get("style") or {}
        # Assign roles if missing
        needs_role = ("color" in style and "color_role" not in style) or (
            "background_color" in style and "background_color_role" not in style
        )
        if needs_role:
            migrate_note_colors(entity)
            changed = True
        # Arrow legacy color -> style.color_role minimal mapping
        if entity.get("type_name") == "Arrow" and "color" in entity:
            base = entity.get("color")
            if isinstance(base, list) and len(base) >= 3:
                rgba = list(base[:4])
                if len(rgba) == 3:
                    rgba.append(1.0 if max(rgba) <= 1.0 else 255)
                if max(rgba) <= 1.0:
                    role = legacy_normalized_rgba_to_role(rgba)
                else:
                    int_list = [int(round(c)) for c in rgba[:4]]
                    while len(int_list) < 4:
                        int_list.append(255)
                    int_rgba = (int_list[0], int_list[1], int_list[2], int_list[3])
                    role = approximate_rgba_to_role(int_rgba)
                st = entity.get("style") or {}
                st.setdefault("color_role", role)
                entity["style"] = st
            del entity["color"]
            changed = True

    for coll in ["children", "notes", "arrows"]:
        items = data.get(coll)
        if isinstance(items, list):
            for ent in items:
                _process(ent)

    if changed:
        backup = p.with_suffix(p.suffix + ".bak")
        if not backup.exists():
            p.write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
            )  # temp write
            # Actually save backup of original by rewriting original first
            backup.write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
        with p.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        log.info(f"Retrofit applied to {p}")
    else:
        log.info(f"Retrofit no changes for {p}")
    return p


# Backward-compat alias (used by DesktopImporter and other callers)
adapt_v4_element_to_v5 = convert_v4_to_v5_element


def migrate_v4_to_v5(repo_path: Path) -> list[Path]:
    """Top-level migration: convert all .pam4.json files in repo_path to .pam5.json.

    For each V4 page file:
      1. Convert to V5 via convert_v4_page_file
      2. Back up the original into __v4_legacy_pages_backup__/
      3. Remove the original .pam4.json

    Returns list of created .pam5.json paths.
    """
    repo_path = Path(repo_path)
    v4_backup_folder = repo_path / "__v4_legacy_pages_backup__"

    v4_pages = [
        f for f in repo_path.iterdir() if f.is_file() and f.name.endswith(V4_FILE_EXT)
    ]

    if not v4_pages:
        return []

    log.info(f"migrate_v4_to_v5: converting {len(v4_pages)} page(s) in {repo_path}")
    converted = []

    for v4_path in v4_pages:
        try:
            # Read the page data to get the id for the new filename
            with open(v4_path, "r", encoding="utf-8") as f:
                page_data = json.load(f)
            page_id = page_data["id"]

            # V5 files are named by page id only
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
