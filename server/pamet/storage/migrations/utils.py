"""Shared utilities for migrations"""

from __future__ import annotations

import shutil
from pathlib import Path

from sivkit.logging import get_logger
from sivkit.util import get_new_id

log = get_logger(__name__)


def new_id_for_legacy_note(note_id, timestamp, content: str, all_ids: list):
    """Generate deterministic ID for duplicate notes.

    Used across multiple migrations to handle duplicate note IDs consistently.
    Creates IDs based on: note_id + timestamp, or note_id + timestamp + content
    if there's a collision.

    Args:
        note_id: Original note ID
        timestamp: Note creation timestamp
        content: Note content (used for additional uniqueness)
        all_ids: List of existing IDs to avoid collisions

    Returns:
        A unique deterministic ID
    """
    note_id = str(note_id)
    timestamp = str(timestamp)
    new_id = get_new_id(note_id + timestamp)
    if new_id in all_ids:
        new_id = get_new_id(note_id + timestamp + str(content))
        if new_id in all_ids:
            raise Exception("Could not generate unique ID for duplicate note")
    return new_id


def backup_file(file_path: Path, backup_folder: Path) -> Path:
    """Backup a file to the backup folder preserving the original filename.

    If a backup with the same name already exists, appends a unique ID to avoid
    conflicts.

    Args:
        file_path: Path to file to backup
        backup_folder: Folder to store the backup

    Returns:
        Path to the created backup file
    """
    backup_folder.mkdir(parents=True, exist_ok=True)
    backup_path = backup_folder / file_path.name

    if backup_path.exists():
        backup_name = f"{file_path.stem}-{get_new_id()}{file_path.suffix}"
        backup_path = backup_folder / backup_name

    shutil.copy(file_path, backup_path)
    log.info(f"Backed up file {file_path} to {backup_path}")
    return backup_path
