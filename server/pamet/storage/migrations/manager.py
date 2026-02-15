from __future__ import annotations

# from hashlib import md5
import shutil
from collections import defaultdict
from pathlib import Path

from fusion.logging import get_logger
from fusion.util import get_new_id
from slugify import slugify

from .v4_to_v5 import is_v4_page_file, migrate_v4_to_v5

log = get_logger(__name__)

# Map from source version to detection function.
# Only V4→V5 is automatic; V2→V3 and V3→V4 are manual.
LEGACY_CHECK_MAP = {
    4: is_v4_page_file,
}

V4_FILE_EXT = ".pam4.json"
V5_FILE_EXT = ".pam5.json"

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


"""old_color_to_role now imported from color_roles (legacy_normalized_rgba_to_role)."""


def backup_file(file_path: Path, backup_folder: Path):
    backup_folder.mkdir(parents=True, exist_ok=True)
    backup_path = backup_folder / (file_path.name + ".backup")
    if backup_path.exists():
        backup_name = backup_path.stem + f".backup-{get_new_id()}"
        backup_path = backup_folder / backup_name

    shutil.copy(file_path, backup_path)
    log.info(f"Backed up file {file_path} to {backup_path}")

    return backup_path


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
    slug = slugify(page.name, separator="_", max_length=100)
    filename = f"{slug}-{page.id}{V5_FILE_EXT}"
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
        modules. This method only handles V4→V5 automatically.
        """
        converted = migrate_v4_to_v5(self.repo_path)
        if converted:
            log.info(f"V4→V5 migration converted {len(converted)} page(s)")
        return converted

    # def checksum_imported_page_notes(self, fs_repo, page: Page):
    #     """
    #     This method should be called by FSStorageRepository after migrations are complete.
    #     It requires an active repo instance to work.
    #     """
    #     note_count_in_repo = len(
    #         [nt for nt in fs_repo.find(parent_gid=page.gid()) if isinstance(nt, Note)]
    #     )

    #     if page.name in self.v2_note_checksum_by_page_name:
    #         v2_note_count = self.v2_note_checksum_by_page_name[page.name]
    #         assert note_count_in_repo == v2_note_count

    #     if page.name in self.v3_note_checksum_by_page_name:
    #         v3_note_count = self.v3_note_checksum_by_page_name[page.name]
    #         assert note_count_in_repo == v3_note_count
