"""Ephemeral backend state, synchronized alongside config but never persisted."""

from typing import Literal, TypedDict

import attrs
from sivkit import Entity, entity_type


class FileSaveErrorData(TypedDict):
    id: str
    path: str
    message: str


class ProjectProblem(TypedDict):
    kind: Literal["unreadable_file", "unlisted_folder", "duplicate_id"]
    path: str  # Relative to the project root
    reason: str


class FileSystemState(TypedDict):
    """The same nested shape in the filesystem owner, entity and wire data."""

    saving: bool
    errors: dict[str, FileSaveErrorData]  # page id → error
    problems: dict[str, ProjectProblem]  # path → problem


class BackupServiceState(TypedDict):
    backups_enabled: bool
    backup_folder: str
    error: str | None


@entity_type
class DesktopStorageState(Entity):
    id: str = "desktop-storage-state"
    closing: bool = False
    config_errors: dict[str, str] = attrs.Factory(dict)


@entity_type
class ProjectStorageState(Entity):
    project_id: str = ""
    phase: Literal["loading", "open", "closing"] = "loading"
    filesystem: FileSystemState | None = None
    backup: BackupServiceState | None = None
    history_error: str | None = None

    @staticmethod
    def id_for_project(project_id: str) -> str:
        return f"project-storage-state-{project_id}"


def is_service_state_id(entity_id: str) -> bool:
    return entity_id == "desktop-storage-state" or entity_id.startswith(
        "project-storage-state-"
    )
