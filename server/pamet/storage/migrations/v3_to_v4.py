"""V3 to V4 Migration

See pamet/wiki/migrations/v3-to-v4.md for detailed documentation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path

from sivkit.logging import get_logger
from sivkit.util import current_time, get_new_id, timestamp
from sivkit.util.point2d import Point2D
from sivkit.util.rectangle import Rectangle
from slugify import slugify

from pamet.constants import (
    MAX_NOTE_HEIGHT,
    MAX_NOTE_WIDTH,
    MIN_NOTE_HEIGHT,
    MIN_NOTE_WIDTH,
)
from pamet.util import snap_to_grid

from .utils import backup_file, new_id_for_legacy_note

log = get_logger(__name__)

V3_BACKUP_FOLDER_NAME = "__v3_legacy_pages_backup__"

# Constants
TIME_FORMAT = "%d.%m.%Y %H:%M:%S"
ONE_V3_COORD_UNIT_TO_V4 = 20

INTERNAL_ANCHOR_PREFIX = "this_note_points_to:"
EXTERNAL_ANCHOR_PREFIX = "define_web_page_note:"
IMAGE_NOTE_PREFIX = "define_picture_note:"
SYSTEM_CALL_NOTE_PREFIX = "define_system_call_note:"

# Module-level state tracking
v3_note_checksum_by_page_name: dict[str, int] = {}


# V4 Data structures (self-contained in migration file)
class ArrowAnchorType(str, Enum):
    """Arrow anchor positions"""

    TOP_MID = "TOP_MID"
    BOTTOM_MID = "BOTTOM_MID"
    MID_LEFT = "MID_LEFT"
    MID_RIGHT = "MID_RIGHT"


@dataclass
class V4Page:
    """V4 Page representation for migration"""

    id: str
    name: str
    datetime_created: str  # ISO format timestamp
    datetime_modified: str  # ISO format timestamp

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "created": self.datetime_created,
            "modified": self.datetime_modified,
            "type_name": "Page",
        }


@dataclass
class V4Note:
    """V4 Note representation for migration"""

    id: tuple[str, str]  # (page_id, note_id)
    type_name: str
    geometry: list[float]  # [x, y, width, height]
    color: list[float]
    background_color: list[float]
    created: str  # ISO format timestamp
    modified: str  # ISO format timestamp
    tags: list = field(default_factory=list)

    # Type-specific fields
    text: str = ""
    url: str = ""
    image_url: str = ""
    local_image_url: str = ""
    script_path: str = ""
    command_args: str = ""

    @property
    def own_id(self) -> str:
        return self.id[1]

    @property
    def page_id(self) -> str:
        return self.id[0]

    def rect(self) -> Rectangle:
        """Return Rectangle for geometry calculations"""
        return Rectangle(
            self.geometry[0], self.geometry[1], self.geometry[2], self.geometry[3]
        )

    def center(self) -> Point2D:
        """Calculate center point"""
        return self.rect().center()

    def to_dict(self) -> dict:
        """Convert to V4 on-disk JSON format (nested style/content/metadata)."""
        style: dict = {
            "color": self.color,
            "background_color": self.background_color,
        }

        content: dict = {}
        if self.text:
            content["text"] = self.text
        if self.url:
            content["url"] = self.url
        if self.image_url:
            content["image_url"] = self.image_url
        if self.local_image_url:
            content["local_image_url"] = self.local_image_url
        if self.script_path:
            content["script_path"] = self.script_path
        if self.command_args:
            content["command_args"] = self.command_args

        return {
            "id": list(self.id),
            "geometry": self.geometry,
            "style": style,
            "content": content,
            "metadata": {},
            "created": self.created,
            "modified": self.modified,
            "tags": self.tags,
            "type_name": self.type_name,
        }


@dataclass
class V4Arrow:
    """V4 Arrow representation for migration"""

    id: tuple[str, str]  # (page_id, arrow_id)
    page_id: str
    tail_note_id: str
    head_note_id: str
    tail_anchor_type: ArrowAnchorType = ArrowAnchorType.MID_RIGHT
    head_anchor_type: ArrowAnchorType = ArrowAnchorType.MID_LEFT
    midpoints: list[list[float]] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to V4 on-disk JSON format."""
        return {
            "id": list(self.id),
            "tail_coords": None,
            "tail_note_id": self.tail_note_id,
            "tail_anchor": self.tail_anchor_type.name,
            "mid_point_coords": self.midpoints,
            "head_coords": None,
            "head_note_id": self.head_note_id,
            "head_anchor": self.head_anchor_type.name,
            "color": None,
            "line_type": None,
            "line_thickness": 1.5,
            "line_function_name": "bezier_cubic",
            "head_shape": None,
            "tail_shape": None,
            "type_name": "Arrow",
        }


def _path_for_page(page: V4Page, repo_path: Path) -> Path:
    """Calculate V4 storage path for a page"""
    slug = slugify(page.name, separator="_", max_length=100)
    filename = f"{slug}-{page.id}.pam4.json"
    return repo_path / filename


def _serialize_v4_page(page: V4Page, notes: list[V4Note], arrows: list[V4Arrow]) -> str:
    """Serialize V4 page to JSON string"""
    page_dict = page.to_dict()
    page_dict["notes"] = [note.to_dict() for note in notes]
    page_dict["arrows"] = [arrow.to_dict() for arrow in arrows]
    return json.dumps(page_dict, indent=4, ensure_ascii=False)


def convert_v3_to_v4_in_memory(
    page_name: str,
    page_data: dict,
) -> tuple[V4Page, list[V4Note], list[V4Arrow]]:
    """Convert a V3 page dict to V4 structures, purely in memory.

    Args:
        page_name: The page name (used for ID generation and logging)
        page_data: Parsed V3 JSON dict (must have "notes" key)

    Returns:
        (V4Page, list[V4Note], list[V4Arrow])
    """
    # V3 example: {
    # "is_displayed_first_on_startup": true
    # "notes": [
    # {"bg_col": [0,0,1,0.1],
    #     "font_size": 1,
    #     "height": 3,
    #     "id": 1,
    #     "links": [
    #         {
    #             "cp": [
    #                 12.25,
    #                 -7.25
    #             ],
    #             "text": "", #             "to_id": 1
    #         }
    #     ],
    #     "t_made": "10.4.2019 14:2:2",
    #     "t_mod": "10.4.2019 14:2:2",
    #     "tags": [],
    #     "text"his_note_points_to:notes",
    #     "txt_col": [0,0,1,1],
    #     "h": 11,
    #     "x": 1,
    #     "y": -2.5}]}

    notes_data = page_data.pop("notes") if "notes" in page_data else []

    # Create V4 page
    page_id = get_new_id(page_name)
    v3_note_checksum_by_page_name[page_name] = 0

    # Load the notes and arrows
    earliest_creation_time = current_time()
    notes: list[V4Note] = []
    arrows: list[V4Arrow] = []
    notes_by_id: dict[str, V4Note] = {}
    ids_with_duplicates: list[str] = []
    new_ids_by_old: dict[str, str] = {}

    for nt in notes_data:
        v3_note_checksum_by_page_name[page_name] += 1

        # Scale old coords so that default widget fonts look adequate without correction
        for coord in ["x", "y", "width", "height"]:
            nt[coord] = snap_to_grid(nt[coord] * ONE_V3_COORD_UNIT_TO_V4)

            # There was that very specific case with an overflow, wtf
            if not (-2147483647 < nt[coord] < 2147483647):
                nt[coord] = 1

        # Transform note data
        note_id = (page_id, str(nt["id"]))
        color = nt.pop("txt_col")
        background_color = nt.pop("bg_col")
        geometry = [nt.pop("x"), nt.pop("y"), nt.pop("width"), nt.pop("height")]
        t_made = nt.pop("t_made")
        t_mod = nt.pop("t_mod")
        tags = nt.pop("tags", [])

        if not t_made:
            log.warning(f"In page {page_name}: Note {nt} is missing t_made")
            t_made = datetime.strftime(current_time(), TIME_FORMAT)
        if not t_mod:
            log.warning(f"In page {page_name}: Note {nt} is missing t_mod")
            t_mod = datetime.strftime(current_time(), TIME_FORMAT)

        created = datetime.strptime(t_made, TIME_FORMAT)
        modified = datetime.strptime(t_mod, TIME_FORMAT)
        # Use the local timezone
        created = created.astimezone()
        modified = modified.astimezone()

        created_ts = timestamp(created)
        modified_ts = timestamp(modified)

        nt.pop("font_size", None)

        if created < earliest_creation_time:
            earliest_creation_time = created

        # Extract arrows from note
        legacy_arrows = nt.pop("links")
        for legacy_arrow in legacy_arrows:
            midpoints = []
            control_point = legacy_arrow.get("cp")
            if control_point:
                midpoint = [
                    control_point[0] * ONE_V3_COORD_UNIT_TO_V4,
                    control_point[1] * ONE_V3_COORD_UNIT_TO_V4,
                ]
                midpoints = [midpoint]

            arrow = V4Arrow(
                id=(page_id, ""),  # Will be set later with deterministic ID
                page_id=page_id,
                tail_note_id=note_id[1],
                head_note_id=str(legacy_arrow["to_id"]),
                midpoints=midpoints,
            )
            arrows.append(arrow)

        # Create note based on type (determined by text prefix)
        note_text = nt.pop("text")
        note: V4Note | None = None

        # Internal anchors - keep original text format for now, will be converted in post-migration
        if note_text.startswith(INTERNAL_ANCHOR_PREFIX):
            note = V4Note(
                id=note_id,
                type_name="TextNote",
                geometry=geometry,
                color=color,
                background_color=background_color,
                created=created_ts,
                modified=modified_ts,
                tags=tags,
                text=note_text,  # Keep original "this_note_points_to:PageName" format
            )

        # External anchors (web links)
        elif note_text.startswith(EXTERNAL_ANCHOR_PREFIX):
            lines = note_text.split("\n")
            url = ""
            text = ""
            for line in lines:
                if line.startswith("url="):
                    url = line[4:]
                elif line.startswith("name="):
                    text = line[5:]

            note = V4Note(
                id=note_id,
                type_name="TextNote",
                geometry=geometry,
                color=color,
                background_color=background_color,
                created=created_ts,
                modified=modified_ts,
                tags=tags,
                url=url,
                text=text,
            )

        # Image notes
        elif note_text.startswith(IMAGE_NOTE_PREFIX):
            image_url = note_text[len(IMAGE_NOTE_PREFIX) :]
            note = V4Note(
                id=note_id,
                type_name="ImageNote",
                geometry=geometry,
                color=color,
                background_color=background_color,
                created=created_ts,
                modified=modified_ts,
                tags=tags,
                image_url=image_url,
                local_image_url=image_url,
            )

        # System call notes
        elif note_text.startswith(SYSTEM_CALL_NOTE_PREFIX):
            script = note_text[len(SYSTEM_CALL_NOTE_PREFIX) :]
            script_parts = script.split()
            command_args = " ".join(script_parts[1:]) if len(script_parts) > 1 else ""

            note = V4Note(
                id=note_id,
                type_name="ScriptNote",
                geometry=geometry,
                color=color,
                background_color=background_color,
                created=created_ts,
                modified=modified_ts,
                tags=tags,
                script_path=script_parts[0] if script_parts else "",
                command_args=command_args,
                text=note_text,
            )

        else:  # It's just a text note
            note = V4Note(
                id=note_id,
                type_name="TextNote",
                geometry=geometry,
                color=color,
                background_color=background_color,
                created=created_ts,
                modified=modified_ts,
                tags=tags,
                text=note_text,
            )

        # Detect duplicate ids
        if note.own_id in notes_by_id:
            ids_with_duplicates.append(note.own_id)
            log.warning(
                f"Detected duplicate for note {note.own_id}. "
                f"Links to/from it will be deleted."
            )

        old_id = note.own_id
        new_id = new_id_for_legacy_note(
            note.own_id,
            note.created,
            note.text or note.image_url or note.script_path,
            list(notes_by_id.keys()),
        )
        note.id = (page_id, new_id)
        new_ids_by_old[old_id] = note.own_id

        # Check note sizes
        width = note.geometry[2]
        height = note.geometry[3]
        width_clamped = max(min(width, MAX_NOTE_WIDTH), MIN_NOTE_WIDTH)
        height_clamped = max(min(height, MAX_NOTE_HEIGHT), MIN_NOTE_HEIGHT)

        if width_clamped != width or height_clamped != height:
            log.info(
                f"Note with invalid size imported. "
                f"Old: {width, height}; New: {width_clamped, height_clamped}"
            )
            note.geometry[2] = width_clamped
            note.geometry[3] = height_clamped

        notes.append(note)
        notes_by_id[note.own_id] = note

    # Remove arrows which start or end at notes with duplicate ids
    arrows = [
        a
        for a in arrows
        if a.tail_note_id not in ids_with_duplicates
        and a.head_note_id not in ids_with_duplicates
    ]

    # Fix arrow note IDs and infer anchor types
    for arrow in arrows:
        # Fix arrow ids (since we changed the note ids)
        arrow.tail_note_id = new_ids_by_old[arrow.tail_note_id]
        arrow.head_note_id = new_ids_by_old[arrow.head_note_id]

        tail_note = notes_by_id[arrow.tail_note_id]
        head_note = notes_by_id[arrow.head_note_id]

        tail_rect = tail_note.rect()
        head_rect = head_note.rect()

        # To check if the notes are above one another - move to the same
        # height and check for an intersection
        intersect_check_rect = Rectangle(
            head_rect.x(), tail_rect.y(), head_rect.width(), head_rect.height()
        )

        if tail_rect.intersects(intersect_check_rect):
            if head_rect.center().y() < tail_rect.center().y():
                arrow.tail_anchor_type = ArrowAnchorType.TOP_MID
                arrow.head_anchor_type = ArrowAnchorType.BOTTOM_MID
            else:
                arrow.tail_anchor_type = ArrowAnchorType.BOTTOM_MID
                arrow.head_anchor_type = ArrowAnchorType.TOP_MID
        elif head_rect.right() <= tail_rect.left():
            arrow.tail_anchor_type = ArrowAnchorType.MID_LEFT
            arrow.head_anchor_type = ArrowAnchorType.MID_RIGHT
        elif head_rect.left() >= tail_rect.right():
            arrow.tail_anchor_type = ArrowAnchorType.MID_RIGHT
            arrow.head_anchor_type = ArrowAnchorType.MID_LEFT
        else:
            # Fallback for edge cases
            arrow.tail_anchor_type = ArrowAnchorType.MID_RIGHT
            arrow.head_anchor_type = ArrowAnchorType.MID_LEFT

    # Update the arrow ids to be deterministic
    arrows_with_new_ids: list[V4Arrow] = []
    arrows_by_id: dict[str, V4Arrow] = {}
    for arrow in arrows:
        new_id = get_new_id([arrow.tail_note_id, arrow.head_note_id])
        if new_id in arrows_by_id:
            # This means there's a second arrow with the same start and
            # end. We just remove it.
            continue
        arrows_by_id[new_id] = arrow
        arrow.id = (page_id, new_id)
        arrows_with_new_ids.append(arrow)
    arrows = arrows_with_new_ids

    # Create the V4 page with inferred timestamps
    page_created_ts = timestamp(earliest_creation_time - timedelta(seconds=10))
    page_modified_ts = timestamp(earliest_creation_time - timedelta(seconds=10))

    page = V4Page(
        id=page_id,
        name=page_name,
        datetime_created=page_created_ts,
        datetime_modified=page_modified_ts,
    )

    return page, notes, arrows


def convert_v3_to_v4(json_path: str | Path, backup_folder: Path, repo_path: Path):
    json_path = Path(json_path)
    page_data = json.loads(json_path.read_text())
    page_name = json_path.stem

    page, notes, arrows = convert_v3_to_v4_in_memory(page_name, page_data)

    # Calculate path and serialize
    new_path = _path_for_page(page, repo_path)
    new_path.parent.mkdir(parents=True, exist_ok=True)

    page_json_str = _serialize_v4_page(page, notes, arrows)
    new_path.write_text(page_json_str)

    backup_file(json_path, backup_folder)
    log.info(f"Converted V3 page {json_path} to V4 at {new_path}")
    json_path.unlink()

    return new_path


def migrate_v3_to_v4(repo_path: Path) -> list[Path]:
    """Migrate all V3 files in a repository to V4 format.

    Args:
        repo_path: Path to the repository root

    Returns:
        List of paths to successfully migrated V4 files
    """
    global v3_note_checksum_by_page_name

    repo_path = Path(repo_path)
    backup_folder = repo_path / V3_BACKUP_FOLDER_NAME

    # Reset migration state
    v3_note_checksum_by_page_name.clear()

    # Collect V3 files (flat .json files, not in subdirectories)
    v3_files = []
    for file in repo_path.iterdir():
        if not file.is_file():
            continue
        if file.suffix == ".json":
            v3_files.append(file)

    if not v3_files:
        log.info("No V3 (.json) files found for migration")
        return []

    log.info(f"Starting V3→V4 migration for {len(v3_files)} files")

    migrated_files = []
    failed_files = []

    for file_path in v3_files:
        try:
            new_path = convert_v3_to_v4(file_path, backup_folder, repo_path)
            migrated_files.append(new_path)
            log.info(f"✓ Migrated: {file_path.name} → {new_path.name}")
        except Exception as e:
            failed_files.append((file_path, str(e)))
            log.error(f"✗ Failed to migrate {file_path.name}: {e}")

    # Summary
    log.info(
        f"V3→V4 migration complete: {len(migrated_files)} succeeded, "
        f"{len(failed_files)} failed"
    )

    if failed_files:
        log.warning("Failed migrations:")
        for file_path, error in failed_files:
            log.warning(f"  - {file_path.name}: {error}")

    # Post-migration: Fix internal page links
    if migrated_files:
        log.info("Fixing internal page links...")
        _fix_internal_page_links(repo_path, migrated_files)

    return migrated_files


def _fix_internal_page_links(repo_path: Path, page_files: list[Path]) -> None:
    """Fix internal page links after V3→V4 migration.

    V3→V4 migration preserves "this_note_points_to:PageName" text format.
    This function extracts the page name, converts it to a proper V4 page URL
    like "project:/page/<page_id>", and moves it to the url field.

    Args:
        repo_path: Repository root path
        page_files: List of migrated .pam4.json page files
    """
    # Build a map of page_name → page_id by reading all page files
    page_name_to_id = {}

    for page_file in page_files:
        try:
            page_data = json.loads(page_file.read_text())
            page_name = page_data.get("name")
            page_id = page_data.get("id")
            if page_name and page_id:
                page_name_to_id[page_name] = page_id
        except Exception as e:
            log.error(f"Failed to read page {page_file.name}: {e}")
            continue

    # Now scan all pages and fix internal links
    total_links_fixed = 0

    for page_file in page_files:
        try:
            page_data = json.loads(page_file.read_text())
            notes = page_data.get("notes", [])
            modified = False

            for note in notes:
                # Check if note has the internal link text prefix
                text = note.get("text", "")

                if text.startswith(INTERNAL_ANCHOR_PREFIX):
                    # Extract page name from "this_note_points_to:PageName"
                    page_name = text[len(INTERNAL_ANCHOR_PREFIX) :]

                    if page_name in page_name_to_id:
                        target_page_id = page_name_to_id[page_name]
                        note["url"] = f"project:/page/{target_page_id}"
                        note["text"] = (
                            ""  # Clear the text field now that we have the URL
                        )
                        modified = True
                        total_links_fixed += 1
                        log.debug(
                            f"Fixed internal link: {page_name} → project:/page/{target_page_id}"
                        )
                    else:
                        log.warning(
                            f"Page name '{page_name}' not found in migrated pages"
                        )

            if modified:
                # Write back the modified page
                json_str = json.dumps(page_data, indent=4, ensure_ascii=False)
                page_file.write_text(json_str)
                log.info(f"Updated internal links in {page_file.name}")

        except Exception as e:
            log.error(f"Failed to fix links in {page_file.name}: {e}")
            continue

    if total_links_fixed:
        log.info(f"Fixed {total_links_fixed} internal page links")
