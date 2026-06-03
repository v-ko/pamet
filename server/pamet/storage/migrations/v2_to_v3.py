"""V2 to V3 Migration

See pamet/wiki/migrations/v2-to-v3.md for detailed documentation.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from pathlib import Path

from sivkit.util import get_new_id
from sivkit.util.point2d import Point2D

from .utils import backup_file, new_id_for_legacy_note

log = logging.getLogger(__name__)

V2_BACKUP_FOLDER_NAME = "__v2_legacy_pages_backup__"

# Module-level state tracking for migration
note_checksum_by_page_name: dict[str, int] = {}
notes_by_page_name: dict[str, set[int]] = defaultdict(set)


def parse_v2_to_v3_dict(
    misl_file_string: str,
    page_name: str,
) -> dict | None:
    """Parse V2 legacy Misli format (.misl) text into a V3 page dict.

    Pure in-memory transform — no filesystem access.

    Args:
        misl_file_string: Contents of a .misl file
        page_name: Stem of the file (used for state tracking / dedup)

    Returns:
        V3 page dict with "notes" list, or None if this is a timeline file.
    """
    # Example V2 file structure:
    # [79367]
    # txt=this_note_points_to:Програмиране
    # x=-7
    # y=-4.5
    # z=0
    # a=9
    # b=2.5
    # font_size=1
    # t_made=6.10.2019 14:1:12
    # t_mod=6.10.2019 14:1:12
    # txt_col=0;0;1;1
    # bg_col=0;0;1;0.100008
    # l_id=
    # l_txt=
    # l_CP_x=
    # l_CP_y=
    # tags=

    # Initialize state tracking
    note_checksum_by_page_name[page_name] = 0
    if page_name not in notes_by_page_name:
        notes_by_page_name[page_name] = set()

    is_displayed_first_on_startup = False
    is_a_timeline_notefile = False

    # Clear the windows standart junk
    # The \r chars should be handled by python
    # misl_file_string = misl_file_string.replace('\r', '')

    lines = [ln for ln in misl_file_string.split("\n") if ln]  # Skip empty

    lines_left = []
    for line in lines:
        if line.startswith("#"):  # Skip comments
            continue

        elif line.startswith("is_displayed_first_on_startup"):
            is_displayed_first_on_startup = True
            continue

        elif line.startswith("is_a_timeline_note_file"):
            is_a_timeline_notefile = True
            continue

        lines_left.append(line)

    if is_a_timeline_notefile:
        return None

    # Extract groups
    notes = defaultdict(dict)
    current_note_id = None
    changed_note_ids = []
    meta_for_id_replace = {}  # Gets assigned the target id
    for line in lines_left:

        if line.startswith("[") and line.endswith("]"):
            current_note_id = int(line[1:-1])

            if current_note_id in notes_by_page_name[page_name]:
                changed_note_ids.append(current_note_id)
                old_id = current_note_id
                current_note_id = get_new_id()
                if current_note_id in meta_for_id_replace:
                    raise Exception("Not enough randomness in ID generation")
                meta_for_id_replace[current_note_id] = old_id

            note_checksum_by_page_name[page_name] += 1
            notes_by_page_name[page_name].add(current_note_id)
            continue

        if "=" not in line:
            raise Exception(
                f"Expected key=value in page {page_name!r}, "
                f"note [{current_note_id}], got: {line!r}"
            )

        [key, value] = line.split("=", 1)

        # Drop some unused fields
        if key in ["z", "l_txt"]:
            continue

        # Convert values where needed
        elif key == "txt":
            value = value.replace("\\n", "\n")
        elif key in ["txt_col", "bg_col"]:
            value = [float(channel) for channel in value.split(";")]
        elif key in ["l_id", "l_CP_x", "l_CP_y"]:
            value = value.split(";")
            value = [v for v in value if v]
            if key == "l_id":
                value = [int(v) for v in value]
            else:
                value = [float(v) for v in value]
        elif key == "id":
            value = int(value)
        elif key in ["x", "y", "a", "b"]:
            value = float(value)
        elif key in ["tags", "font_size", "t_mod", "t_made"]:
            pass
        else:
            raise Exception(
                f"Unknown key {key!r} in page {page_name!r}, "
                f"note [{current_note_id}], value: {value!r}"
            )

        notes[current_note_id][key] = value

    # Notes with duplicate ids first get a random id and then we
    # replace it with a deterministic id based on
    # id, timestamp, text
    for nt_random_id, old_id in meta_for_id_replace.items():
        nt = notes.pop(nt_random_id)
        note_id = new_id_for_legacy_note(
            old_id, nt["t_made"], nt["txt"], list(notes.keys())
        )
        notes[note_id] = nt

    for note_id, nt in notes.items():
        # Rename fields to the V3 schema
        nt["id"] = note_id
        nt["width"] = nt.pop("a")
        nt["height"] = nt.pop("b")
        nt["text"] = nt.pop("txt")

        # Process arrows (formerly named links)
        control_points = []
        if "l_CP_x" in nt and "l_CP_y" in nt:
            for cp_x, cp_y in zip(nt["l_CP_x"], nt["l_CP_y"]):
                control_points.append(Point2D(cp_x, cp_y))
        else:
            control_points = None

        to_ids = nt.pop("l_id")
        cp_xs = nt.pop("l_CP_x", None)
        cp_ys = nt.pop("l_CP_y", None)

        if cp_xs and cp_ys:
            CPs = list(zip(cp_xs, cp_ys))
            if len(to_ids) != len(CPs):
                raise Exception(
                    f"Mismatch between link IDs and control points in note {note_id}"
                )
        else:
            CPs = None

        nt["links"] = []
        for i, to_id in enumerate(to_ids):
            if to_id in changed_note_ids:  # Skip links of buggy notes
                continue
            link_dict = {"text": "", "to_id": to_id}
            if CPs:
                link_dict["cp"] = CPs[i]

            nt["links"].append(link_dict)

    # Verification
    assert len(notes) == len(notes_by_page_name[page_name])
    assert len(notes) == note_checksum_by_page_name[page_name]

    page_dict: dict = {"notes": list(notes.values())}
    if is_displayed_first_on_startup:
        page_dict["is_displayed_first_on_startup"] = True

    return page_dict


def convert_v2_to_v3(file_path: Path, backup_folder: Path) -> Path | None:
    """Migrate from V2 legacy Misli format (.misl) to V3 JSON format.

    Args:
        file_path: Path to the .misl file to migrate
        backup_folder: Folder to store backups of original files

    Returns:
        Path to the created V3 .json file, or None if skipped (timeline file)

    Handles:
    - INI-like .misl file parsing
    - Duplicate note ID resolution
    - Property transformations (a→width, b→height, txt→text, etc.)
    - Arrow/link extraction from embedded note properties
    - Color format conversion (semicolon-separated to arrays)
    - State tracking for verification

    For detailed documentation see: pamet/wiki/migrations/v2-to-v3.md
    """
    file_path = Path(file_path)
    page_name = file_path.stem
    misl_file_string = file_path.read_text()

    page_dict = parse_v2_to_v3_dict(misl_file_string, page_name)
    if page_dict is None:
        return None

    new_path = file_path.with_suffix(".json")
    json_str = json.dumps(page_dict, indent=4, ensure_ascii=False)
    new_path.write_text(json_str)
    log.info(f"Converted v2 file at {file_path} to v3 file at {new_path}")

    backup_file(file_path, backup_folder)
    file_path.unlink()

    return new_path


def migrate_v2_to_v3(repo_path: Path) -> list[Path]:
    """Migrate all V2 files in a repository to V3 format.

    Args:
        repo_path: Path to the repository root

    Returns:
        List of paths to successfully migrated V3 files
    """
    global note_checksum_by_page_name, notes_by_page_name

    repo_path = Path(repo_path)
    backup_folder = repo_path / V2_BACKUP_FOLDER_NAME

    # Reset migration state
    note_checksum_by_page_name.clear()
    notes_by_page_name.clear()

    # Collect V2 files
    v2_files = []
    for file in repo_path.iterdir():
        if not file.is_file():
            continue
        if file.suffix == ".misl":
            v2_files.append(file)

    if not v2_files:
        log.info("No V2 (.misl) files found for migration")
        return []

    log.info(f"Starting V2→V3 migration for {len(v2_files)} files")

    migrated_files = []
    failed_files = []

    for file_path in v2_files:
        try:
            new_path = convert_v2_to_v3(file_path, backup_folder)
            if new_path:
                migrated_files.append(new_path)
                log.info(f"✓ Migrated: {file_path.name} → {new_path.name}")
        except Exception as e:
            failed_files.append((file_path, str(e)))
            log.error(f"✗ Failed to migrate {file_path.name}: {e}")

    # Summary
    log.info(
        f"V2→V3 migration complete: {len(migrated_files)} succeeded, "
        f"{len(failed_files)} failed"
    )

    if failed_files:
        log.warning("Failed migrations:")
        for file_path, error in failed_files:
            log.warning(f"  - {file_path.name}: {error}")

    return migrated_files
