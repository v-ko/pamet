from __future__ import annotations

import logging
import threading
from pathlib import Path

from sivkit.storage.delta import Delta
from sivkit.storage.in_memory_store import InMemoryStore
from sivkit.storage.websocket_sync_service import WebSocketSyncService

from pamet.model.config import ProjectProperties
from pamet.model.page import Page
from pamet.services.config_file_manager import ConfigFileManager, DSSStatus
from pamet.services.full_change_history_service import FullChangeHistoryService
from pamet.services.project_sync.project_folder_manager import ProjectFolderManager

log = logging.getLogger(__name__)


class ProjectNotLoadedError(KeyError):
    pass


class DesktopStorageService:
    def __init__(self):
        self._project_folder_managers: dict[str, ProjectFolderManager] = {}
        self._change_history_services: dict[str, FullChangeHistoryService] = {}
        self._lock = threading.RLock()

        # Status object — services write errors here, exposed via /status
        self.status: DSSStatus = {"errors": {}, "backup_service": {}}
        self.status["errors"]["config_file_manager"] = {}

        # Config store: holds UserSettings, DeviceState, ProjectProperties
        self._config_store = InMemoryStore()
        self._config_file_manager = ConfigFileManager(
            store=self._config_store,
            resolve_project_path=self._resolve_project_path,
            status_errors=self.status["errors"]["config_file_manager"],
        )
        self._config_sync_service = WebSocketSyncService(
            self._config_store, role="authority"
        )

        # Wire persistence: store changes → file manager + backup config watcher
        self._config_store.add_on_changes_callback(self._on_config_changes)

        # Load existing config from disk
        self._config_file_manager.load_app_config(self._config_store)

    def change_history_service(
        self, project_id: str
    ) -> FullChangeHistoryService | None:
        """Return the change history service for a project, or None if disabled."""
        with self._lock:
            return self._change_history_services.get(project_id)

    @property
    def config_sync_service(self) -> WebSocketSyncService:
        return self._config_sync_service

    @property
    def config_store(self) -> InMemoryStore:
        return self._config_store

    def _resolve_project_path(self, project_id: str) -> Path | None:
        """Resolve a project ID to its repo root path."""
        with self._lock:
            pfm = self._project_folder_managers.get(project_id)
            if pfm is not None:
                return pfm.repo_root
        return None

    def _on_config_changes(self, delta: Delta, origin: str | None = None) -> None:
        """Chained config store callback: persist to disk + react to settings."""
        if origin == "remote":
            entity_ids = [c.entity_id for c in delta.changes()]
            log.warning(
                "_on_config_changes: REMOTE delta from client! entities=%s",
                entity_ids,
            )
        self._config_file_manager.on_changes(delta, origin)
        self._apply_backup_settings_from_delta(delta)
        self._apply_change_history_settings_from_delta(delta)

    def _apply_backup_settings_from_delta(self, delta: Delta) -> None:
        """Check if any ProjectProperties changed and update backup_service.backups_enabled."""
        for change in delta.changes():
            entity_id = change.entity_id
            if not entity_id.startswith("project-props-"):
                continue
            project_id = entity_id.removeprefix("project-props-")
            with self._lock:
                pfm = self._project_folder_managers.get(project_id)
                if pfm is None:
                    continue
            # Read the current entity from the store
            entity = self._config_store.find_one(id=entity_id)
            if entity is not None and isinstance(entity, ProjectProperties):
                try:
                    pfm.backup_service.backups_enabled = entity.backups_enabled
                    # Update status
                    if project_id in self.status["backup_service"]:
                        self.status["backup_service"][project_id][
                            "backups_enabled"
                        ] = entity.backups_enabled
                except Exception as exc:
                    msg = (
                        f"Backup service toggle failed for project {project_id}: {exc}"
                    )
                    log.error(msg)
                    self.status["errors"].setdefault("backup_service", {})
                    self.status["errors"]["backup_service"][project_id] = msg

    def _apply_change_history_settings_from_delta(self, delta: Delta) -> None:
        """Enable or disable the change history service when record_all_changes changes."""
        for change in delta.changes():
            entity_id = change.entity_id
            if not entity_id.startswith("project-props-"):
                continue
            project_id = entity_id.removeprefix("project-props-")
            with self._lock:
                pfm = self._project_folder_managers.get(project_id)
                if pfm is None:
                    continue
            entity = self._config_store.find_one(id=entity_id)
            if entity is not None and isinstance(entity, ProjectProperties):
                try:
                    self._set_change_history_enabled(
                        project_id, pfm.repo_root, entity.record_all_changes
                    )
                except Exception as exc:
                    msg = (
                        f"Change history toggle failed for project {project_id}: {exc}"
                    )
                    log.error(msg)
                    self.status["errors"].setdefault("change_history", {})
                    self.status["errors"]["change_history"][project_id] = msg

    def _set_change_history_enabled(
        self, project_id: str, repo_root: Path, enabled: bool
    ) -> None:
        with self._lock:
            existing = self._change_history_services.get(project_id)
            if enabled and existing is None:
                db_path = repo_root / ".pamet" / "change-history.db"
                svc = FullChangeHistoryService(db_path)
                self._change_history_services[project_id] = svc
                if svc.is_healthy:
                    log.info(
                        "Change history enabled for project %s (db: %s)",
                        project_id,
                        db_path,
                    )
                else:
                    log.error(
                        "Change history unhealthy for project %s: %s",
                        project_id,
                        svc.error,
                    )
                    self.status["errors"].setdefault("change_history", {})
                    self.status["errors"]["change_history"][project_id] = svc.error
            elif not enabled and existing is not None:
                existing.close()
                del self._change_history_services[project_id]
                log.info("Change history disabled for project %s", project_id)

    def load_project(self, project_id: str, repo_root: Path) -> None:
        """Load a project fully (blocking). Use load_project_fs + load_project_config
        for async endpoints where the event loop must stay free."""
        self.load_project_fs(project_id, repo_root)
        self.load_project_config(project_id)

    def load_project_fs(self, project_id: str, repo_root: Path) -> None:
        """Blocking phase: read .canvas files from disk, create PFM.

        After this returns the PFM is registered but config store has NOT
        been updated (no WebSocket delta is fired).
        """
        with self._lock:
            if project_id in self._project_folder_managers:
                log.info(
                    "DesktopStorageService load_project is idempotent for %s",
                    project_id,
                )
                return
            if not repo_root.is_absolute():
                raise ValueError("repo_root must be an absolute path")

            pfm = ProjectFolderManager(
                project_id=project_id,
                repo_root=repo_root,
            )
            pfm.load()
            self._project_folder_managers[project_id] = pfm

    def load_project_config(self, project_id: str) -> None:
        """Event-loop phase: update config store and apply settings.

        Must be called AFTER load_project_fs. This modifies the config store,
        which fires on_changes → WebSocket push_delta.  Safe to call on the
        event loop since it does no blocking I/O.
        """
        with self._lock:
            pfm = self._project_folder_managers.get(project_id)
            if pfm is None:
                log.warning("load_project_config: PFM not found for %s", project_id)
                return

            # Check if entity already exists before loading
            project_properties_key = ProjectProperties.id_for_project(project_id)
            existing = self._config_store.find_one(id=project_properties_key)
            if existing:
                log.warning(
                    "load_project_config: entity ALREADY in store before load "
                    "(home_page_id=%r). Something else created it!",
                    getattr(existing, "home_page_id", "N/A"),
                )

            # Load project properties into the config store
            self._config_file_manager.load_project_properties(
                self._config_store,
                project_id,
            )

            # Ensure project properties exist in the store
            project_properties_key = ProjectProperties.id_for_project(project_id)
            props = self._config_store.find_one(id=project_properties_key)
            if props is None:
                # No properties file on disk — create default entity
                props = ProjectProperties(
                    id=project_properties_key,
                    project_id=project_id,
                    title=pfm.repo_root.name,
                )
                self._config_store.insert_one(props)

            # If no home page set, pick the first available page
            if isinstance(props, ProjectProperties) and not props.home_page_id:
                first_page = next(pfm.store.find(type=Page), None)
                if first_page is not None:
                    props.home_page_id = first_page.id
                    self._config_store.update_one(props)
                    log.info(
                        "load_project_config: auto-set home_page_id=%s for %s",
                        props.home_page_id,
                        project_id,
                    )

            log.info(
                "load_project_config: props in store for %s: %s (home_page_id=%s)",
                project_id,
                props is not None,
                getattr(props, "home_page_id", "N/A") if props else "N/A",
            )
            try:

                if props is not None and isinstance(props, ProjectProperties):
                    pfm.backup_service.backups_enabled = props.backups_enabled
                else:
                    pfm.backup_service.backups_enabled = True
            except Exception as exc:
                msg = f"Backup service failed to start for project {project_id}: {exc}"
                log.error(msg)
                self.status["errors"].setdefault("backup_service", {})
                self.status["errors"]["backup_service"][project_id] = msg

            # Register backup service status
            self.status["backup_service"][project_id] = {
                "present": True,
                "backups_enabled": pfm.backup_service.backups_enabled,
                "backup_folder": str(pfm.backup_service.backup_folder),
            }

            # Apply change history settings from loaded project properties
            try:
                if props is not None and isinstance(props, ProjectProperties):
                    log.info(
                        "load_project %s: record_all_changes=%s",
                        project_id,
                        props.record_all_changes,
                    )
                    self._set_change_history_enabled(
                        project_id, pfm.repo_root, props.record_all_changes
                    )
                else:
                    log.info(
                        "load_project %s: no ProjectProperties found (props=%r)",
                        project_id,
                        props,
                    )
            except Exception as exc:
                msg = f"Change history failed to start for project {project_id}: {exc}"
                log.error(msg)
                self.status["errors"].setdefault("change_history", {})
                self.status["errors"]["change_history"][project_id] = msg

            log.info(
                "DesktopStorageService loaded ProjectFolderManager for %s",
                project_id,
            )

    def unload_project(self, project_id: str) -> None:
        with self._lock:
            # Tear down change history if active
            chs = self._change_history_services.pop(project_id, None)
            if chs is not None:
                chs.close()

            pfm = self._project_folder_managers.pop(project_id, None)
            if pfm is None:
                return
            pfm.unload()
            self.status["backup_service"].pop(project_id, None)
            log.info(
                "DesktopStorageService unloaded ProjectFolderManager for %s",
                project_id,
            )

    def project_folder_manager(self, project_id: str) -> ProjectFolderManager:
        with self._lock:
            pfm = self._project_folder_managers.get(project_id)
            if pfm is None:
                raise ProjectNotLoadedError(
                    f"No active project runtime for '{project_id}'"
                )
            return pfm
