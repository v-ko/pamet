"""
V4 to current canvas migration for Pamet pages (.pam4.json -> .canvas).

Handles: composite ID flattening, color role conversion, note type unification,
image metadata restructuring, internal URL rewrite, arrow endpoint restructuring,
repo properties rename (`.pamet/settings.json` -> `.pamet/properties.json`).

Image notes are migrated to page-scoped `ImageItem` entities embedded in the
page payload, and legacy `project.pamet.json` sidecar data is folded into the
page payloads as well.

The element migration logic mirrors the TypeScript tmpDynamicMigration in
web-app/src/storage/DesktopImporter.ts.
"""

import copy
import hashlib
import json
import mimetypes
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fusion.logging import get_logger
from fusion.util import get_new_id

from pamet.storage.migrations.utils import backup_file

from ..file_system.color_roles import legacy_normalized_rgba_to_role

log = get_logger(__name__)

V4_FILE_EXT = ".pam4.json"
CANVAS_FILE_EXT = ".canvas"
PAGE_SCHEMA_VERSION = 5

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

LEGACY_PROJECT_CONFIG_FILENAME = "project.pamet.json"
REPO_PROPERTIES_FILENAME = "properties.json"
LEGACY_REPO_SETTINGS_FILENAME = "settings.json"
V4_BACKUP_FOLDER_NAME = "__migration_backup_v4_to_v5__"


def is_v4_page_file(path: Path) -> bool:
    """Check if the path is a V4 page file that needs migration."""
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
            content["image"] = {
                "url": image_url,
                "width": width,
                "height": height,
                "_original_url": local_image_url,
            }
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
            "note_anchor_id": element_data.get("tail_note_id"),
            "note_anchor_type": (element_data.get("tail_anchor", "none").lower()),
        }
        element_data["head"] = {
            "position": element_data.get("head_coords"),
            "note_anchor_id": element_data.get("head_note_id"),
            "note_anchor_type": (element_data.get("head_anchor", "none").lower()),
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


def _resolve_original_image_url(original_url: str, repo_path: Path) -> Optional[Path]:
    """Resolve a V4 local_image_url to an absolute file path.

    V4 scheme (ground truth: tests/mock_v4_project/original/repo/.pamet/media/):
    - ``pamet:/p/{namespace}/media/{filename}``  →  ``<repo>/.pamet/media/{namespace}/{filename}``
      The ``/media/`` segment in the URL is redundant; disk layout is flat under the namespace.
    - absolute filesystem path  →  ``Path(abs_path)``

    Returns None for http(s) or unrecognised schemes.
    """
    if original_url.startswith("pamet:/p/"):
        rest = original_url[len("pamet:/p/") :]
        # V4 URLs have a redundant /media/ segment: {namespace}/media/{filename}
        # Actual disk path is .pamet/media/{namespace}/{filename}
        parts = rest.split("/media/", 1)
        if len(parts) == 2:
            namespace, filename = parts
            return repo_path / ".pamet" / "media" / namespace / filename
        return repo_path / ".pamet" / "media" / rest

    if original_url.startswith("/"):
        return Path(original_url)

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
    parent_id: str,
    width: int,
    height: int,
) -> Dict[str, Any]:
    """Build a plain dict matching the ImageItem entity schema."""
    content_hash = _compute_content_hash(file_path)
    size = file_path.stat().st_size
    mime = _guess_mime(file_path)

    return {
        "id": get_new_id(),
        "parent_id": parent_id,
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
):
    """Second pass over canvas pages: create page-scoped ImageItem dicts and rewrite notes.

    For each note with ``content.image``:
    - Resolve the URL to a file on disk.
    - If the file exists: compute hash, get dimensions, build an ImageItem dict,
      replace ``content.image`` with ``content.image_id``.
    - If external: copy the file into ``<repo>/images/``.
    - If not found: set ``content.text`` to an error message, log warning.

    Persist the generated ImageItem dicts directly in the page payload.
    """
    repo_path = Path(repo_path)

    for v5_path in v5_page_paths:
        try:
            _migrate_image_notes_for_page(v5_path, repo_path)
        except Exception as exc:
            log.error(f"migrate_image_notes: failed processing {v5_path}: {exc}")


def _migrate_image_notes_for_page(v5_path: Path, repo_path: Path):
    try:
        with open(v5_path, "r", encoding="utf-8") as f:
            page_data = json.load(f)
    except Exception as exc:
        log.error(f"migrate_image_notes: failed to read {v5_path}: {exc}")
        return

    modified = False
    page_id = page_data.get("id")
    if not page_id:
        log.error(f"migrate_image_notes: page missing id in {v5_path}")
        return
    note_states = page_data.setdefault("notes", [])
    file_items_states = page_data.setdefault("file_items", [])
    existing_image_item_ids = {
        fi.get("id")
        for fi in file_items_states
        if isinstance(fi, dict) and fi.get("type_name") == "ImageItem"
    }

    for note in list(note_states):
        content = note.get("content")
        if not content or not isinstance(content.get("image"), dict):
            continue

        original_url = content.get("image", {}).get("_original_url") or content.get(
            "image", {}
        ).get("url", "?")
        try:
            modified |= _migrate_single_image_note(
                note,
                content,
                repo_path,
                page_id,
                file_items_states,
                existing_image_item_ids,
            )
        except Exception as exc:
            log.error(
                f"  note {note.get('id')}: image migration failed: {exc} "
                f"(url: {original_url})"
            )
            content.pop("image", None)
            error_text = f"[Image migration error ({original_url}): {exc}]"
            if content.get("text"):
                content["text"] += "\n" + error_text
            else:
                content["text"] = error_text
            modified = True

    if modified:
        with open(v5_path, "w", encoding="utf-8") as f:
            json.dump(page_data, f, indent=2, ensure_ascii=False)


def _migrate_single_image_note(
    note: Dict,
    content: Dict,
    repo_path: Path,
    page_id: str,
    file_items_states: List,
    existing_image_item_ids: set,
) -> bool:
    image_info = content["image"]
    original_url = image_info.pop("_original_url", None) or image_info.get("url", "")
    v4_width = image_info.get("width", 0)
    v4_height = image_info.get("height", 0)

    # Skip external web URLs
    if original_url.startswith("http://") or original_url.startswith("https://"):
        log.info(
            f"  note {note['id']}: external web URL, "
            f"keeping content.image as-is: {original_url}"
        )
        return False

    file_path = _resolve_original_image_url(original_url, repo_path)

    if file_path is None:
        log.warning(
            f"  note {note['id']}: unrecognised image URL scheme: {original_url}"
        )
        return False

    if not file_path.exists():
        log.warning(
            f"  note {note['id']}: image file not found: {file_path} "
            f"(url: {original_url})"
        )
        content.pop("image", None)
        error_text = f"[Image not found at migration time: {original_url}]"
        if content.get("text"):
            content["text"] += "\n" + error_text
        else:
            content["text"] = error_text
        return True

    # Copy all images into <repo>/images/
    images_dir = repo_path / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    dest = images_dir / file_path.name
    # Avoid name collisions
    if dest.exists() and dest.read_bytes() != file_path.read_bytes():
        stem = file_path.stem
        suffix = file_path.suffix
        counter = 1
        while dest.exists():
            dest = images_dir / f"{stem}_{counter}{suffix}"
            counter += 1
    if not dest.exists():
        shutil.copy2(file_path, dest)
    rel_path = str(dest.relative_to(repo_path))

    # Get real dimensions (prefer Pillow, fall back to V4 metadata)
    pil_w, pil_h = _get_image_dimensions(file_path)
    width = pil_w if pil_w > 0 else int(v4_width)
    height = pil_h if pil_h > 0 else int(v4_height)

    item_dict = _build_image_item_dict(
        file_path=dest,
        rel_path=rel_path,
        parent_id=page_id,
        width=width,
        height=height,
    )
    if item_dict["id"] in existing_image_item_ids:
        log.warning(f"  note {note['id']}: duplicate ImageItem id generated, skipping")
        return False

    file_items_states.append(item_dict)
    existing_image_item_ids.add(item_dict["id"])

    # Rewrite the note
    content.pop("image", None)
    content["image_id"] = item_dict["id"]

    log.info(
        f"  note {note['id']}: created ImageItem {item_dict['id']} "
        f"-> {rel_path} (from: {original_url})"
    )
    return True


def _collect_canvas_page_paths(repo_path: Path) -> List[Path]:
    return sorted(
        [
            path
            for path in repo_path.iterdir()
            if path.is_file() and path.name.endswith(CANVAS_FILE_EXT)
        ]
    )


def _migrate_repo_settings_keys(properties_path: Path) -> None:
    """Rename legacy keys in a properties.json file (e.g. home_page -> default_page_id)."""
    try:
        with open(properties_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return
    if not isinstance(data, dict):
        return
    changed = False
    if "home_page" in data:
        if "default_page_id" not in data:
            data["default_page_id"] = data.pop("home_page")
        else:
            del data["home_page"]
        changed = True
    if changed:
        with open(properties_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)


def migrate_repo_properties_file(repo_path: Path, backup_folder: Path) -> bool:
    pamet_dir = repo_path / ".pamet"
    legacy_path = pamet_dir / LEGACY_REPO_SETTINGS_FILENAME
    properties_path = pamet_dir / REPO_PROPERTIES_FILENAME

    if not legacy_path.exists():
        # Even if already migrated, rename home_page → default_page_id if needed
        if properties_path.exists():
            _migrate_repo_settings_keys(properties_path)
        return False

    if properties_path.exists():
        backup_file(legacy_path, backup_folder)
        legacy_path.unlink()
        _migrate_repo_settings_keys(properties_path)
        log.info(
            "migrate_v4_to_v5: removed legacy repo settings %s because %s already exists",
            legacy_path.name,
            properties_path.name,
        )
        return True

    pamet_dir.mkdir(parents=True, exist_ok=True)
    backup_file(legacy_path, backup_folder)
    legacy_path.rename(properties_path)
    _migrate_repo_settings_keys(properties_path)
    log.info(
        "migrate_v4_to_v5: migrated repo properties %s -> %s",
        legacy_path.name,
        properties_path.name,
    )
    return True


def migrate_legacy_project_config(
    repo_path: Path, canvas_page_paths: List[Path], backup_folder: Path
) -> bool:
    project_config_path = repo_path / LEGACY_PROJECT_CONFIG_FILENAME
    if not project_config_path.exists():
        return False

    try:
        with open(project_config_path, "r", encoding="utf-8") as f:
            project_config = json.load(f)
    except Exception as exc:
        log.error(f"migrate_v4_to_v5: failed to read {project_config_path.name}: {exc}")
        return False

    image_items = project_config.get("image_items", [])
    if not isinstance(image_items, list):
        image_items = []

    if not image_items:
        backup_file(project_config_path, backup_folder)
        project_config_path.unlink()
        log.info(
            "migrate_v4_to_v5: removed empty legacy project config %s",
            project_config_path.name,
        )
        return True

    note_page_by_image_id: dict[str, str] = {}
    page_data_by_path: dict[Path, dict[str, Any]] = {}
    page_path_by_id: dict[str, Path] = {}

    for canvas_path in canvas_page_paths:
        try:
            with open(canvas_path, "r", encoding="utf-8") as f:
                page_data = json.load(f)
        except Exception as exc:
            log.error(f"migrate_v4_to_v5: failed to read {canvas_path}: {exc}")
            continue
        page_id = page_data.get("id")
        if not page_id:
            continue
        page_data_by_path[canvas_path] = page_data
        page_path_by_id[page_id] = canvas_path
        for note_state in page_data.get("notes", []):
            if not isinstance(note_state, dict):
                continue
            if note_state.get("type_name") == "ImageItem":
                continue
            content = note_state.get("content")
            if isinstance(content, dict):
                image_id = content.get("image_id")
                if isinstance(image_id, str) and image_id:
                    note_page_by_image_id[image_id] = page_id

    attached_count = 0
    for image_item in image_items:
        if not isinstance(image_item, dict):
            continue
        image_id = image_item.get("id")
        if not isinstance(image_id, str) or not image_id:
            continue
        page_id = note_page_by_image_id.get(image_id)
        if not page_id:
            log.warning(
                f"migrate_v4_to_v5: legacy ImageItem {image_id} has no referencing note; skipping"
            )
            continue
        canvas_path = page_path_by_id.get(page_id)
        if canvas_path is None:
            continue
        page_data = page_data_by_path[canvas_path]
        file_items_list = page_data.setdefault("file_items", [])
        if any(
            isinstance(fi, dict) and fi.get("id") == image_id for fi in file_items_list
        ):
            continue
        migrated_item = copy.deepcopy(image_item)
        migrated_item["parent_id"] = page_id
        file_items_list.append(migrated_item)
        attached_count += 1

    for canvas_path, page_data in page_data_by_path.items():
        with open(canvas_path, "w", encoding="utf-8") as f:
            json.dump(page_data, f, indent=2, ensure_ascii=False)

    backup_file(project_config_path, backup_folder)
    project_config_path.unlink()
    log.info(
        "migrate_v4_to_v5: folded %s legacy ImageItem(s) from %s into page payloads",
        attached_count,
        project_config_path.name,
    )
    return True


def convert_v4_to_v5_page_dict(page_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a v4 page dict to current canvas schema."""
    result = copy.deepcopy(page_data)

    page_id = result.get("id")
    if not page_id:
        raise ValueError("Page missing 'id'")

    if "children" in result:
        migrated_children = [
            convert_v4_to_v5_element(ch, page_id) for ch in result["children"]
        ]
        result["notes"] = [
            child
            for child in migrated_children
            if not isinstance(child, dict)
            or child.get("type_name") not in ("Arrow", "FileItem", "ImageItem")
        ]
        result["arrows"] = [
            child
            for child in migrated_children
            if isinstance(child, dict) and child.get("type_name") == "Arrow"
        ]
        result["file_items"] = [
            child
            for child in migrated_children
            if isinstance(child, dict)
            and child.get("type_name") in ("FileItem", "ImageItem")
        ]
        result.pop("children", None)
    else:
        all_notes = [
            convert_v4_to_v5_element(n, page_id) for n in result.get("notes", [])
        ]
        result["notes"] = [
            n
            for n in all_notes
            if not isinstance(n, dict)
            or n.get("type_name") not in ("FileItem", "ImageItem")
        ]
        result["file_items"] = [
            n
            for n in all_notes
            if isinstance(n, dict) and n.get("type_name") in ("FileItem", "ImageItem")
        ]
        result["arrows"] = [
            convert_v4_to_v5_element(a, page_id) for a in result.get("arrows", [])
        ]

    result.setdefault("type_name", "Page")
    result["schema_version"] = PAGE_SCHEMA_VERSION
    return result


def convert_v4_page_file(v4_file_path: Path, v5_file_path: Path) -> Path:
    """Convert a single .pam4.json file to .canvas."""
    with open(v4_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data = convert_v4_to_v5_page_dict(data)
    with open(v5_file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return v5_file_path


def migrate_v4_to_v5(repo_path: Path) -> List[Path]:
    """Convert all .pam4.json files in repo_path to .canvas.

    For each V4 page file:
      1. Convert to current canvas format
      2. Back up the original into __migration_backup_v4_to_v5__/
      3. Remove the original .pam4.json

    Returns list of created .canvas paths.
    """
    repo_path = Path(repo_path)
    v4_backup_folder = repo_path / V4_BACKUP_FOLDER_NAME

    v4_pages = [
        f for f in repo_path.iterdir() if f.is_file() and f.name.endswith(V4_FILE_EXT)
    ]
    migrate_repo_properties_file(repo_path, v4_backup_folder)

    converted = []
    if v4_pages:
        log.info(f"migrate_v4_to_v5: converting {len(v4_pages)} page(s) in {repo_path}")

        for v4_path in v4_pages:
            try:
                with open(v4_path, "r", encoding="utf-8") as f:
                    page_data = json.load(f)
                page_id = page_data["id"]

                v5_path = v4_path.parent / (page_id + CANVAS_FILE_EXT)
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

    if converted:
        migrate_image_notes(repo_path, converted)

    canvas_page_paths = _collect_canvas_page_paths(repo_path)
    if canvas_page_paths:
        migrate_legacy_project_config(repo_path, canvas_page_paths, v4_backup_folder)

    return converted
