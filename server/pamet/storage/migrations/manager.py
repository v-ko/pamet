from __future__ import annotations

import json
from pathlib import Path

from fusion.logging import get_logger

from .v2_to_v3 import V2_BACKUP_FOLDER_NAME
from .v3_to_v4 import V3_BACKUP_FOLDER_NAME
from .v4_to_v5 import (
    V4_BACKUP_FOLDER_NAME,
    is_v4_page_file,
    migrate_v4_to_v5,
)

log = get_logger(__name__)

MIGRATION_BACKUP_DIR_NAMES = {
    V2_BACKUP_FOLDER_NAME,
    V3_BACKUP_FOLDER_NAME,
    V4_BACKUP_FOLDER_NAME,
}

# Map from legacy format to detection function.
# V2→V3 and V3→V4 remain manual.
LEGACY_CHECK_MAP = {
    4: is_v4_page_file,
}

V4_FILE_EXT = ".pam4.json"

LEGACY_REPO_SETTINGS_FILE = "settings.json"
REPO_PROPERTIES_FILE = "properties.json"


class MigrationManager:
    """Runs storage format migrations (V4→V5 canvas conversion).

    V2→V3 and V3→V4 migrations are manual — see their standalone modules."""

    def __init__(self, repo_path: Path) -> None:
        self.repo_path = Path(repo_path)

    def entry_is_legacy(self, entry_path: Path):
        """Check if the path matches any known legacy format that needs migration."""
        for check_func in LEGACY_CHECK_MAP.values():
            if check_func(entry_path):
                return True
        return False

    def do_all_migrations(self):
        """
        Performs automatic migrations for supported legacy versions.

        NOTE: V2→V3 and V3→V4 migrations are NOT included here due to safety
        concerns — those should be performed manually using their standalone
        modules. This method handles V4→current canvas format only.
        """
        converted_v4 = migrate_v4_to_v5(self.repo_path)
        if converted_v4:
            log.info(f"V4→Canvas migration converted {len(converted_v4)} page(s)")
        return converted_v4


def get_project_id_from_repo_settings(repo_path: Path) -> str | None:
    repo_path = Path(repo_path)
    pamet_dir = repo_path / ".pamet"
    for file_name in (REPO_PROPERTIES_FILE, LEGACY_REPO_SETTINGS_FILE):
        settings_path = pamet_dir / file_name
        if not settings_path.exists():
            continue
        with settings_path.open() as settings_file:
            settings_data = json.load(settings_file)
        project_id = settings_data.get("id")
        if isinstance(project_id, str) and project_id.strip():
            return project_id
    return None
