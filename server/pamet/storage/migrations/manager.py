from __future__ import annotations

# from hashlib import md5
from collections import defaultdict
import json
from pathlib import Path

from fusion.logging import get_logger
from fusion.util import get_new_id
from .v4_to_v5 import (
    CANVAS_FILE_EXT,
    is_v4_page_file,
    migrate_v4_to_v5,
)

log = get_logger(__name__)

# Map from legacy format to detection function.
# V2→V3 and V3→V4 remain manual.
LEGACY_CHECK_MAP = {
    4: is_v4_page_file,
}

V4_FILE_EXT = ".pam4.json"
V5_FILE_EXT = CANVAS_FILE_EXT

_cache = {}
_paths_cache = {}
MAX_CACHE = 1000
new_to_old_path = {}
md5_by_old_name = {}

# # Caching - to be removed. it's only for the bin import
# def get_from_cache(page_path: Path):
#     if page_md5 in _cache:
#         return _cache[page_md5]
#     return page_md5

TIME_FORMAT = "%d.%m.%Y %H:%M:%S"
ONE_V3_COORD_UNIT_TO_V4 = 20

INTERNAL_ANCHOR_PREFIX = "this_note_points_to:"
EXTERNAL_ANCHOR_PREFIX = "define_web_page_note:"
IMAGE_NOTE_PREFIX = "define_picture_note:"
SYSTEM_CALL_NOTE_PREFIX = "define_system_call_note:"

# Default color roles for v4 to v5 migration
DEFAULT_TEXT_COLOR_ROLE = "onPrimary"
DEFAULT_BACKGROUND_COLOR_ROLE = "primary"

LEGACY_REPO_SETTINGS_FILE = "settings.json"
REPO_PROPERTIES_FILE = "properties.json"


"""old_color_to_role now imported from color_roles (legacy_normalized_rgba_to_role)."""


def new_legacy_id_for_legacy_note(
    note_id: int, timestamp: str, text: str, all_ids: list
):
    # Make a deterministic new id based on the timestamp and old id
    new_id = hash(timestamp)
    if new_id in all_ids:
        # If that's not enough - add a suffix based on the note text
        new_id = hash(timestamp + text)
        if new_id in all_ids:  # Mostly for timeline notes
            new_id = hash(get_new_id())
            if new_id in all_ids:
                raise Exception("WTF")

    return new_id


def new_id_for_legacy_note(note_id, timestamp, content: str, all_ids: list):
    # Make a deterministic new id based on the timestamp and old id
    note_id = str(note_id)
    timestamp = str(timestamp)
    new_id = get_new_id(note_id + timestamp)
    if new_id in all_ids:
        # If that's not enough - add a suffix based on the note text
        new_id = get_new_id(note_id + timestamp + str(content))
        if new_id in all_ids:  # Mostly for timeline notes
            raise Exception("WTF")

    return new_id


def path_for_page(page, repo_path: Path) -> Path:
    """Standalone function to calculate the file path for a page"""
    filename = f"{page.id}{V5_FILE_EXT}"
    return repo_path / filename


class MigrationManager:
    """The storage format migrations mostly translate from one format to another where
    the serialization format and model change (only on major version releases).

    The class tracks the legacy files. One way to do that is via the check_entry function
    that calls all checking functions for the respective legacy versions. The point is to
    be able to do the check efficiently while the ProjectFolder manager is doing its scanning.
      The other way is to call a dedicated reindexing. That's done when doing the migrations
    because each migration produces files in the format of the next version.
    """

    def __init__(self, repo_path: Path) -> None:
        self.repo_path = Path(repo_path)
        self.v2_note_checksum_by_page_name = {}
        self.v3_note_checksum_by_page_name = {}
        self.v2_notes_by_page_name = defaultdict(set)

    def entry_is_legacy(self, entry_path: Path):
        """Check if the path matches any known legacy format that needs migration."""
        for check_func in LEGACY_CHECK_MAP.values():
            if check_func(entry_path):
                return True
        return False

    def index_project_folder(self, folder_path: Path):

        pass

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
