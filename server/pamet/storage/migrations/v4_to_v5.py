"""
V4 to current canvas migration for Pamet pages (.pam4.json -> .canvas).

Handles: composite ID flattening, color role conversion, note type unification,
image metadata restructuring, internal URL rewrite, arrow endpoint restructuring,
repo properties rename (`.pamet/settings.json` -> `.pamet/properties.json`).

Image notes are migrated to inline image references with {path, hash, width, height}
in the note content.

The element migration logic mirrors the TypeScript tmpDynamicMigration in
web-app/src/storage/DesktopImporter.ts.

Also has logic for migrating user settings and the backup folder
"""

import copy
import hashlib
import json
import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sivkit.util import get_new_id
from slugify import slugify

from pamet.storage.canvas_html import write_canvas_file
from pamet.storage.migrations.utils import backup_file

from ..file_system.color_roles import legacy_normalized_rgba_to_role

log = logging.getLogger(__name__)

from pamet.services.constants import CANVAS_FILE_EXT

V4_FILE_EXT = ".pam4.json"
PAGE_SCHEMA_VERSION = 5

DEFAULT_TEXT_COLOR_ROLE = "onDefault"
DEFAULT_BACKGROUND_COLOR_ROLE = "default"

NOTE_LEGACY_TYPES = {
    "TextNote",
    "ImageNote",
    "ScriptNote",
    "CardNote",
    "OtherPageListNote",
}

# SHA-256 truncation length for content hashes (matches TS/constants.py)
_CONTENT_HASH_HEX_LEN = 32

REPO_PROPERTIES_FILENAME = "properties.json"
LEGACY_REPO_SETTINGS_FILENAME = "settings.json"
V4_BACKUP_FOLDER_NAME = "__migration_backup_v4_to_v5__"


def _v4_terminal_prefix_to_template(prefix: str) -> str:
    """Convert a v4 bare prefix string into a v5 ``{cmd}``-template.

    v4 stored e.g. ``'gnome-terminal -- '`` and concatenated the command after
    it. v5 expects a template containing ``{cmd}`` so the runner can substitute
    the assembled (shell-quoted) argv. POSIX prefixes typically end in an
    argument separator that needs a real command after it, so we wrap with
    ``bash -c {cmd}``; Windows shells consume the line as-is.
    """
    if "{cmd}" in prefix:
        return prefix
    suffix = "bash -c {cmd}" if "--" in prefix else "{cmd}"
    return f"{prefix.rstrip()} {suffix}".strip()


def process_v4_user_settings(app_data_dir: Path) -> Optional[Dict[str, Any]]:
    """Read v4 ``settings.json`` and return a sparse v5 *overrides* dict.

    The v4 file lives in the Qt ``GenericDataLocation`` directory (e.g.
    ``~/.local/share/pamet/settings.json`` on Linux), which v5 exposes as
    ``PAMET_APP_DATA_DIR``.

    Returns ``None`` if no legacy file exists. Otherwise returns a dict
    containing only the fields v4 actually carried, ready to be deep-merged
    on top of fresh v5 defaults:

    - ``repository_path`` (top-level convenience for caller; not a UserSettings field)
    - ``scripts.run_in_terminal_prefix.{posix,windows}`` if v4 had non-default
      values

    The v5 structural defaults (``accepted_paths``, ``limits``) are owned by
    :func:`pamet.model.config.default_script_settings` — never reproduced here.
    The v4 ``accepted_script_risks`` boolean is intentionally dropped (logged).
    """
    legacy_path = app_data_dir / "settings.json"
    if not legacy_path.exists():
        return None

    try:
        data = json.loads(legacy_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(
            f"Failed to parse legacy user settings {legacy_path}: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise ValueError(
            f"Expected dict in legacy user settings {legacy_path}, "
            f"got {type(data).__name__}"
        )

    log.info(
        "Migrating v4 user settings from %s: %s",
        legacy_path,
        json.dumps(data, indent=2, sort_keys=True),
    )

    if data.get("accepted_script_risks"):
        log.info(
            "v4->v5: 'accepted_script_risks' is dropped; v5 prompts per-path "
            "and supports per-folder allowlisting."
        )

    overrides: Dict[str, Any] = {
        "repository_path": data.get("repository_path"),
    }

    terminal_prefix: Dict[str, str] = {}
    if "run_in_terminal_prefix_posix" in data:
        terminal_prefix["posix"] = _v4_terminal_prefix_to_template(
            data["run_in_terminal_prefix_posix"]
        )
    if "run_in_terminal_prefix_windows" in data:
        terminal_prefix["windows"] = _v4_terminal_prefix_to_template(
            data["run_in_terminal_prefix_windows"]
        )
    if terminal_prefix:
        overrides["scripts"] = {"run_in_terminal_prefix": terminal_prefix}

    return overrides


V4_USER_SETTINGS_BACKUP_SUFFIX = ".v4.bak"


def archive_v4_user_settings(legacy_path: Path) -> Path:
    """Rename ``legacy_path`` to a sibling ``.v4.bak`` (uniquified on collision).

    Preserved as an audit trail for fields v5 does not carry over (e.g. the
    v4 ``accepted_script_risks`` boolean).
    """
    backup_path = legacy_path.with_suffix(
        legacy_path.suffix + V4_USER_SETTINGS_BACKUP_SUFFIX
    )
    if backup_path.exists():
        backup_path = legacy_path.with_suffix(
            f"{legacy_path.suffix}{V4_USER_SETTINGS_BACKUP_SUFFIX}.{get_new_id()}"
        )
    legacy_path.rename(backup_path)
    log.info("Archived legacy user settings %s -> %s", legacy_path, backup_path)
    return backup_path


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
    element_data: Dict[str, Any],
    page_id: str,
    page_id_to_path: Optional[Dict[str, str]] = None,
    page_id_to_name: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Convert a single V4 element dict to V5 format.

    Handles notes (all legacy types -> CardNote) and arrows.

    *page_id_to_path*, when provided, maps V4 page IDs to their V5
    project-relative ``.canvas`` paths so that ``page_ref.path`` is set
    correctly for internal links.

    *page_id_to_name*, when provided, maps V4 page IDs to their page
    names so that ``content.text`` is set to the target page name for
    internal link notes (matching the TS behaviour).
    """
    if not isinstance(element_data, dict):
        raise TypeError(
            f"Expected dict for element in page {page_id}, "
            f"got {type(element_data).__name__}: {element_data!r}"
        )

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

        # --- ScriptNote: preserve subtype + lift v4 root-level fields into content ---
        # MUST run before the unify-to-CardNote step below.
        if original_type == "ScriptNote":
            sp = element_data.pop("script_path", None)
            ca = element_data.pop("command_args", None)
            rit = element_data.pop("run_in_terminal", None)
            wd = element_data.pop("working_directory", None)

            if sp is not None and sp != "":
                content["script_path"] = str(sp)
            if ca is not None:
                content["command_args"] = str(ca)
            if rit is not None:
                content["run_in_terminal"] = bool(rit)
            if wd is not None and wd != "":
                content["working_directory"] = str(wd)

            element_data["type_name"] = "ScriptNote"
        else:
            # Unify all other legacy note types to CardNote
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
            style["background_color_role"] = "neutral"

        # Internal link URL → page_ref migration
        url = content.get("url")
        if isinstance(url, str) and url.startswith("pamet:/p"):
            # Extract page id from pamet:/p/<page_id> or pamet:/p/<page_id>/...
            parts = url.replace("pamet:/p/", "").split("/")
            if parts and parts[0]:
                target_id = parts[0]
                target_path = (
                    page_id_to_path.get(target_id, target_id + CANVAS_FILE_EXT)
                    if page_id_to_path
                    else target_id + CANVAS_FILE_EXT
                )
                content["page_ref"] = {
                    "id": target_id,
                    "path": target_path,
                }
                # Set link text to target page name (matches TS behaviour).
                # If the target page is missing, mark it as deleted.
                if page_id_to_name and target_id in page_id_to_name:
                    content["text"] = page_id_to_name[target_id]
                else:
                    content["text"] = f"(deleted {target_id})"
            content.pop("url", None)

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
# Image migration helpers (no model dependency — plain dicts)
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


_MAX_IMAGE_FILE_SIZE = 100 * 1024 * 1024  # 100 MB


def _compute_content_hash(file_path: Path) -> str:
    """SHA-256 of file contents, truncated to _CONTENT_HASH_HEX_LEN hex chars."""
    size = file_path.stat().st_size
    if size > _MAX_IMAGE_FILE_SIZE:
        raise ValueError(
            f"Image file too large ({size} bytes, max {_MAX_IMAGE_FILE_SIZE}): "
            f"{file_path}"
        )
    h = hashlib.sha256(file_path.read_bytes()).hexdigest()
    return h[:_CONTENT_HASH_HEX_LEN]


def _get_image_dimensions(file_path: Path) -> Tuple[int, int]:
    """Return (width, height) using Pillow."""
    from PIL import Image

    with Image.open(file_path) as img:
        return img.size  # (width, height)


def _migrate_images_in_page(page_data: Dict[str, Any], repo_path: Path) -> None:
    """Migrate image notes to inline references with {path, hash, width, height}."""
    page_id = page_data.get("id")
    if not page_id:
        return
    note_states = page_data.setdefault("notes", [])
    # Dedup: reuse the same inline ref when multiple notes reference the same source file
    image_ref_by_source: Dict[Path, Dict[str, Any]] = {}

    for note in list(note_states):
        content = note.get("content")
        if not content or not isinstance(content.get("image"), dict):
            continue
        original_url = content["image"].get("_original_url") or content["image"].get(
            "url", "?"
        )
        try:
            _migrate_single_image_note(
                note,
                content,
                repo_path,
                page_id,
                image_ref_by_source,
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


def _migrate_single_image_note(
    note: Dict,
    content: Dict,
    repo_path: Path,
    page_id: str,
    image_ref_by_source: Dict[Path, Dict[str, Any]],
) -> None:
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
        return

    file_path = _resolve_original_image_url(original_url, repo_path)

    if file_path is None:
        log.warning(
            f"  note {note['id']}: unrecognised image URL scheme: {original_url}"
        )
        return

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
        return

    # Reuse existing inline ref if the same source file was already processed
    if file_path in image_ref_by_source:
        ref = image_ref_by_source[file_path]
        content.pop("image", None)
        content["image"] = dict(ref)
        log.info(
            f"  note {note['id']}: reusing image ref for {ref['path']} "
            f"(from: {original_url})"
        )
        return

    # Images under the old internal store (.pamet/) or outside the repo
    # are moved/copied into <repo>/images/.  Everything else already lives
    # in a user-facing project folder and stays in place.
    try:
        rel = file_path.relative_to(repo_path)
        needs_move = rel.parts and rel.parts[0] == ".pamet"
    except ValueError:
        needs_move = True  # outside repo

    if needs_move:
        images_dir = repo_path / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        dest = images_dir / file_path.name
        # Avoid name collisions
        if dest.exists():
            dest_size = dest.stat().st_size
            src_size = file_path.stat().st_size
            if dest_size != src_size or (
                src_size <= _MAX_IMAGE_FILE_SIZE
                and dest.read_bytes() != file_path.read_bytes()
            ):
                stem = file_path.stem
                suffix = file_path.suffix
                counter = 1
                while dest.exists():
                    dest = images_dir / f"{stem}_{counter}{suffix}"
                    counter += 1
        if not dest.exists():
            shutil.copy2(file_path, dest)
        rel_path = str(dest.relative_to(repo_path))
    else:
        dest = file_path
        rel_path = str(rel)

    # Get real dimensions (Pillow, with V4 metadata fallback)
    try:
        width, height = _get_image_dimensions(file_path)
    except Exception as exc:
        log.warning(
            f"  note {note['id']}: Pillow failed for {file_path}: {exc}, "
            f"falling back to V4 metadata"
        )
        width = int(v4_width)
        height = int(v4_height)

    content_hash = _compute_content_hash(dest)

    image_ref = {
        "path": rel_path,
        "width": width,
        "height": height,
        "hash": content_hash,
    }
    image_ref_by_source[file_path] = image_ref

    # Rewrite the note with inline reference
    content.pop("image", None)
    content["image"] = dict(image_ref)

    log.info(
        f"  note {note['id']}: migrated image -> {rel_path} "
        f"(hash: {content_hash}, from: {original_url})"
    )


def _migrate_repo_settings_keys(properties_path: Path, repo_path: Path) -> None:
    """Rename legacy keys and populate title/project_id from the repo folder name."""
    try:
        with open(properties_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        raise ValueError(f"Failed to parse {properties_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(
            f"Expected dict in {properties_path}, got {type(data).__name__}"
        )
    changed = False
    if "home_page" in data:
        data["home_page_id"] = data.pop("home_page")
        changed = True
    # Populate title from the repo folder name if missing or empty
    if not data.get("title"):
        data["title"] = repo_path.name
        changed = True
    # Populate project_id from slugified folder name if missing or empty
    if not data.get("project_id"):
        data["project_id"] = slugify(repo_path.name)
        changed = True
    if changed:
        with open(properties_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)


def migrate_repo_properties_file(repo_path: Path, backup_folder: Path) -> bool:
    pamet_dir = repo_path / ".pamet"
    legacy_path = pamet_dir / LEGACY_REPO_SETTINGS_FILENAME
    properties_path = pamet_dir / REPO_PROPERTIES_FILENAME

    if not legacy_path.exists():
        # Even if already migrated, rename v4 home_page → home_page_id if needed
        if properties_path.exists():
            _migrate_repo_settings_keys(properties_path, repo_path)
        return False

    if properties_path.exists():
        _migrate_repo_settings_keys(properties_path, repo_path)
        backup_file(legacy_path, backup_folder)
        legacy_path.unlink()
        log.info(
            "migrate_v4_to_v5: removed legacy repo settings %s because %s already exists",
            legacy_path.name,
            properties_path.name,
        )
        return True

    pamet_dir.mkdir(parents=True, exist_ok=True)
    backup_file(legacy_path, backup_folder)
    legacy_path.rename(properties_path)
    _migrate_repo_settings_keys(properties_path, repo_path)
    log.info(
        "migrate_v4_to_v5: migrated repo properties %s -> %s",
        legacy_path.name,
        properties_path.name,
    )
    return True


def convert_v4_to_v5_page_dict(
    page_data: Dict[str, Any],
    page_id_to_path: Optional[Dict[str, str]] = None,
    page_id_to_name: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Convert a v4 page dict to current canvas schema."""
    result = copy.deepcopy(page_data)

    page_id = result.get("id")
    if not page_id:
        raise ValueError("Page missing 'id'")

    if "children" in result:
        migrated_children = [
            convert_v4_to_v5_element(ch, page_id, page_id_to_path, page_id_to_name)
            for ch in result["children"]
        ]
        result["notes"] = [
            child
            for child in migrated_children
            if child.get("type_name") not in ("Arrow", "FileItem", "ImageItem")
        ]
        result["arrows"] = [
            child for child in migrated_children if child.get("type_name") == "Arrow"
        ]
        result.pop("children", None)
    else:
        all_notes = [
            convert_v4_to_v5_element(n, page_id, page_id_to_path, page_id_to_name)
            for n in result.get("notes", [])
        ]
        result["notes"] = [
            n for n in all_notes if n.get("type_name") not in ("FileItem", "ImageItem")
        ]
        result["arrows"] = [
            convert_v4_to_v5_element(a, page_id, page_id_to_path, page_id_to_name)
            for a in result.get("arrows", [])
        ]

    result.setdefault("type_name", "Page")
    result["schema_version"] = PAGE_SCHEMA_VERSION
    return result


def migrate_backups_layout(repo_path: Path) -> None:
    """Fix v4 backup folder layout: flatten backups/backups/, fix ++ timestamps,
    and move timestamp files into the backups dir."""
    pamet_dir = repo_path / ".pamet"
    backups_dir = pamet_dir / "backups"
    nested_dir = backups_dir / "backups"

    # Flatten backups/backups/ → backups/
    if nested_dir.is_dir():
        for child in nested_dir.iterdir():
            dest = backups_dir / child.name
            if child.is_dir() and dest.is_dir():
                # Merge contents
                for item in child.iterdir():
                    shutil.move(str(item), str(dest / item.name))
                child.rmdir()
            else:
                shutil.move(str(child), str(dest))
        if nested_dir.exists() and not any(nested_dir.iterdir()):
            nested_dir.rmdir()
        log.info("migrate_backups_layout: flattened backups/backups/")

    if not backups_dir.is_dir():
        return

    # Move timestamp files from .pamet/ into .pamet/backups/
    for ts_file in ("last_backup_timestamp.txt", "last_prune_timestamp.txt"):
        old = pamet_dir / ts_file
        if old.is_file():
            shutil.move(str(old), str(backups_dir / ts_file))

    # Fix ++ timestamps in backup filenames (e.g. "++0200" → "+0200")
    renamed = 0
    for path in backups_dir.rglob("backup_*"):
        if "++" not in path.name:
            continue
        new_name = path.name.replace("++", "+")
        path.rename(path.with_name(new_name))
        renamed += 1
    if renamed:
        log.info(f"migrate_backups_layout: fixed {renamed} backup filename(s)")


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
    try:
        migrate_repo_properties_file(repo_path, v4_backup_folder)
    except Exception as e:
        log.error(f"migrate_v4_to_v5: repo properties migration failed: {e}")

    converted = []
    if v4_pages:
        log.info(f"migrate_v4_to_v5: converting {len(v4_pages)} page(s) in {repo_path}")

        # First pass: build page_id → v5 path map so internal links get
        # correct page_ref.path values (using the page name, not the id).
        page_id_to_path: Dict[str, str] = {}
        page_id_to_name: Dict[str, str] = {}
        used_names: Dict[str, int] = {}  # collision counter
        v4_page_datas: list[tuple[Path, Dict[str, Any]]] = []
        for v4_path in v4_pages:
            try:
                with open(v4_path, "r", encoding="utf-8") as f:
                    page_data = json.load(f)
            except Exception as e:
                log.error(f"  FAILED to read {v4_path.name}: {e}")
                continue
            page_id = page_data.get("id")
            if not page_id:
                log.error(f"  SKIPPING {v4_path.name}: missing page id")
                continue
            page_name = page_data.get("name", page_id)
            # Handle name collisions by appending the page id
            if page_name in used_names:
                page_name = f"{page_name} ({page_id})"
            used_names[page_name] = 1
            v5_rel_path = page_name + CANVAS_FILE_EXT
            page_id_to_path[page_id] = v5_rel_path
            page_id_to_name[page_id] = page_data.get("name", page_id)
            v4_page_datas.append((v4_path, page_data))

        # Second pass: convert and write
        for v4_path, page_data in v4_page_datas:
            try:
                page_id = page_data["id"]

                v5_path = v4_path.parent / page_id_to_path[page_id]
                v5_data = convert_v4_to_v5_page_dict(
                    page_data, page_id_to_path, page_id_to_name
                )
                _migrate_images_in_page(v5_data, repo_path)

                write_canvas_file(v5_path, v5_data)

                backup_file(v4_path, v4_backup_folder)
                v4_path.unlink()
                log.info(f"  {v4_path.name} -> {v5_path.name}")
                converted.append(v5_path)

            except Exception as e:
                log.error(f"  FAILED to convert {v4_path.name}: {e}")
                continue

        log.info(f"migrate_v4_to_v5: done, {len(converted)}/{len(v4_pages)} converted")

    migrate_backups_layout(repo_path)

    return converted
