"""Persists config entities to files based on entity ID routing.

This is an ``on_changes`` subscriber for a config store.  The DSS wires it
to ``store.on_changes`` so that every entity mutation is automatically
persisted to the appropriate JSON file on disk.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypedDict

from sivkit.libs.model import dump_to_dict, load_from_dict
from sivkit.logging import get_logger
from sivkit.storage.delta import Delta
from sivkit.storage.in_memory_store import InMemoryStore

from pamet.desktop_app.config import PAMET_CONFIG_DIR, USER_SETTINGS_DIR

log = get_logger(__name__)

DEVICE_STATE_PATH = PAMET_CONFIG_DIR / "device-state.json"
USER_SETTINGS_PATH = USER_SETTINGS_DIR / "settings.json"


class ServiceErrors(TypedDict, total=False):
    """Error state for a single service. Keys are error type, values are messages."""

    io: str  # e.g. "Permission denied: /path/to/file"


class BackupServiceStatus(TypedDict):
    """Per-project backup service status."""

    present: bool
    backups_enabled: bool
    backup_folder: str  # Absolute path to the backups/ directory


class DSSStatus(TypedDict):
    """Status object for DesktopStorageService, exposed via /status endpoint."""

    errors: dict[str, ServiceErrors]  # service_name → {error_type → message}
    backup_service: dict[str, BackupServiceStatus]  # project_id → status


class ConfigFileManager:
    """Routes config entities to their on-disk JSON files.

    Entity routing:
    - id == ``user-settings``       → ``{CONFIG}/user/settings.json``
    - id == ``device-state``        → ``{CONFIG}/device-state.json``
    - id starts with ``project-props-`` → ``{repo_root}/.pamet/properties.json``
    """

    def __init__(
        self,
        store: InMemoryStore,
        resolve_project_path: Callable[[str], Path | None] | None = None,
        status_errors: ServiceErrors | None = None,
    ) -> None:
        self._store = store
        self._resolve_project_path = resolve_project_path
        self._status_errors = status_errors if status_errors is not None else {}

    def on_changes(self, delta: Delta, origin: str | None = None) -> None:
        """Called by the config store whenever entities change.

        Logic errors (entity not found, bad id pattern) propagate as exceptions.
        I/O errors are logged and recorded in status — the operation is considered
        applied in-memory even if persistence fails.
        """
        for change in delta.changes():
            entity_id = change.entity_id
            if change.is_delete():
                self._delete_file(entity_id)
            else:
                entity = self._store.find_one(id=entity_id)
                if entity is None:
                    raise RuntimeError(
                        f"Entity {entity_id} not found in store after on_changes fired"
                    )
                try:
                    data = dump_to_dict(entity)
                    self._write_file(entity_id, data)
                    # Clear any previous I/O error for this service
                    self._status_errors.pop("io", None)
                except OSError as e:
                    msg = f"Failed to write {entity_id}: {e}"
                    log.error("ConfigFileManager: %s", msg)
                    self._status_errors["io"] = msg

    def load_app_config(self, store: InMemoryStore) -> None:
        """Read app-level config files from disk and populate the store."""
        for path, entity_id in self._app_config_files():
            if not path.exists():
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError(
                    f"Expected dict in config file {path}, got {type(data).__name__}"
                )
            data["id"] = entity_id
            entity = load_from_dict(data)
            if store.find_one(id=entity.id):
                store.update_one(entity)
            else:
                store.insert_one(entity)

    def _app_config_files(self) -> list[tuple[Path, str]]:
        """Return (path, entity_id) pairs for app-level config files."""
        files: list[tuple[Path, str]] = [
            (USER_SETTINGS_PATH, "user-settings"),
            (DEVICE_STATE_PATH, "device-state"),
        ]
        # We don't enumerate project files here — they're loaded on demand
        # when projects are tracked.  DSS can call load_project_properties()
        # for each tracked project.
        return files

    def load_project_properties(self, store: InMemoryStore, project_id: str) -> None:
        """Load a single project's properties from disk into the store."""
        path = self._resolve_path(f"project-props-{project_id}")
        if path is None or not path.exists():
            return
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(
                f"Expected dict in project properties {path}, got {type(data).__name__}"
            )
        entity_id = f"project-props-{project_id}"
        # The on-disk file may be raw project data (no type_name) from
        # migrations or older code paths.  Inject entity metadata so
        # load_from_dict can deserialise it as a ProjectProperties entity.
        data.setdefault("type_name", "ProjectProperties")
        data.setdefault("parent_id", "")
        # Always use the canonical project_id (the one DSS knows about),
        # not whatever "id" the on-disk V4 file might contain.
        data["project_id"] = project_id
        data["id"] = entity_id
        entity = load_from_dict(data)
        if store.find_one(id=entity.id):
            store.update_one(entity)
        else:
            store.insert_one(entity)

    def _resolve_path(self, entity_id: str) -> Path | None:
        if entity_id == "user-settings":
            return USER_SETTINGS_PATH
        elif entity_id == "device-state":
            return DEVICE_STATE_PATH
        elif entity_id.startswith("project-props-"):
            if self._resolve_project_path is None:
                log.warning(
                    "ConfigFileManager: no resolve_project_path callback for %s",
                    entity_id,
                )
                return None
            project_id = entity_id.removeprefix("project-props-")
            repo_root = self._resolve_project_path(project_id)
            if repo_root is None:
                log.warning(
                    "ConfigFileManager: could not resolve repo root for project %s",
                    project_id,
                )
                return None
            return repo_root / ".pamet" / "properties.json"
        else:
            raise ValueError(
                f"ConfigFileManager: unknown entity id pattern: {entity_id}"
            )

    def _write_file(self, entity_id: str, data: dict[str, Any]) -> None:
        path = self._resolve_path(entity_id)
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        # Remove internal fields that shouldn't go to disk
        data_to_write = {k: v for k, v in data.items() if k != "parent_id"}
        path.write_text(
            json.dumps(data_to_write, indent=4, ensure_ascii=False), encoding="utf-8"
        )
        log.info("ConfigFileManager: wrote %s", path)

    def _delete_file(self, entity_id: str) -> None:
        path = self._resolve_path(entity_id)
        if path is None:
            return
        if path.exists():
            path.unlink()
            log.info("ConfigFileManager: deleted %s", path)


# -- Standalone helpers (no store required) --------------------------------


def _read_config_entity(path: Path, entity_id: str):
    """Read a config entity from a JSON file. Returns None if missing."""
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return None
    data["id"] = entity_id
    data.setdefault("parent_id", "")
    if "type_name" not in data:
        # Infer type from entity_id convention
        if entity_id == "user-settings":
            data["type_name"] = "UserSettings"
        elif entity_id == "device-state":
            data["type_name"] = "DeviceState"
    return load_from_dict(data)


def _write_config_entity(path: Path, entity) -> None:
    """Write a config entity to a JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = dump_to_dict(entity)
    data_to_write = {k: v for k, v in data.items() if k != "parent_id"}
    path.write_text(
        json.dumps(data_to_write, indent=4, ensure_ascii=False), encoding="utf-8"
    )


def load_user_settings():
    """Load UserSettings from disk without requiring a store or DSS."""
    return _read_config_entity(USER_SETTINGS_PATH, "user-settings")


def save_user_settings(settings) -> None:
    """Save UserSettings to disk without requiring a store or DSS."""
    _write_config_entity(USER_SETTINGS_PATH, settings)
