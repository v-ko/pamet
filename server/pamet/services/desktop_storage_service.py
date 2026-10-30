from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, TypeVar

from sivkit.storage.delta import Delta
from sivkit.storage.in_memory_store import InMemoryStore
from sivkit.storage.websocket_sync_service import WebSocketSyncService

from pamet.model.config import ProjectProperties
from pamet.model.page import Page
from pamet.model.service_state import (
    DesktopStorageState,
    ProjectStorageState,
    is_service_state_id,
)
from pamet.services.config_file_manager import ConfigFileManager
from pamet.services.full_change_history_service import FullChangeHistoryService
from pamet.services.project_sync.project_folder_manager import (
    ProjectFolderManager,
    scan_project,
)

log = logging.getLogger(__name__)
T = TypeVar("T")


class ProjectNotLoadedError(KeyError):
    pass


class StorageClosingError(RuntimeError):
    pass


@dataclass
class _Project:
    root: Path
    state: Literal["loading", "open", "closing"] = "loading"
    load_task: asyncio.Task | None = None
    unload_task: asyncio.Task | None = None
    pfm: ProjectFolderManager | None = None
    history: FullChangeHistoryService | None = None
    backup_error: str | None = None
    history_error: str | None = None
    close_callbacks: set[Callable[[], None]] = field(default_factory=set)
    pending_operations: set[asyncio.Task] = field(default_factory=set)


def _observe_task(task: asyncio.Task) -> None:
    # The request may have disconnected; still retrieve the owned task's error.
    if not task.cancelled():
        task.exception()


class DesktopStorageService:
    def __init__(self):
        self._projects: dict[str, _Project] = {}
        self.closing = False
        self._close_callbacks: set[Callable[[], None]] = set()
        self._close_task: asyncio.Task | None = None

        # Config and transient backend state share the existing WebSocket store.
        self._config_store = InMemoryStore()
        self._config_file_manager = ConfigFileManager(
            store=self._config_store,
            resolve_project_path=self._resolve_project_path,
            on_state_changed=self._publish_app_state,
        )
        self._config_sync_service = WebSocketSyncService(
            self._config_store, role="authority"
        )

        # Load existing config from disk
        self._config_file_manager.load_app_config(self._config_store)

        # Wire persistence after hydration; reads must not enqueue writes.
        self._config_store.add_on_changes_callback(self._on_config_changes)
        self._publish_app_state()

    def _require_open_project(self, project_id: str) -> _Project:
        project = self._projects.get(project_id)
        if self.closing or (project is not None and project.state == "closing"):
            raise StorageClosingError(f"Desktop project '{project_id}' is closing")
        if project is None or project.state != "open":
            raise ProjectNotLoadedError(f"No active project runtime for '{project_id}'")
        return project

    def change_history_service(self, project_id: str) -> FullChangeHistoryService:
        history = self._require_open_project(project_id).history
        assert history is not None
        return history

    def _publish_app_state(self) -> None:
        self._publish_state(
            DesktopStorageState(
                closing=self.closing,
                config_errors=dict(self._config_file_manager.errors),
            )
        )

    def _publish_state(self, state) -> None:
        existing = self._config_store.find_one(id=state.id)
        if existing is None:
            self._config_store.insert_one(state)
        elif existing.asdict() != state.asdict():
            self._config_store.update_one(state)

    def _publish_project_state(self, project_id: str) -> None:
        project = self._projects[project_id]
        pfm = project.pfm
        self._publish_state(
            ProjectStorageState(
                id=ProjectStorageState.id_for_project(project_id),
                project_id=project_id,
                phase=project.state,
                # Store a snapshot: later runtime mutations must produce a new delta.
                filesystem=deepcopy(pfm.state) if pfm else None,
                backup=(
                    {
                        "backups_enabled": pfm.backup_service.backups_enabled,
                        "backup_folder": str(pfm.backup_service.backup_folder),
                        "error": project.backup_error,
                    }
                    if pfm
                    else None
                ),
                history_error=project.history_error,
            )
        )

    def set_history_error(self, project_id: str, message: str | None) -> None:
        project = self._projects.get(project_id)
        if project is not None:
            project.history_error = message
            self._publish_project_state(project_id)

    @property
    def status(self) -> dict:
        """Diagnostic HTTP snapshot of the same entities sent over config sync."""
        from sivkit.libs.model import dump_to_dict

        return {
            "service": dump_to_dict(
                self._config_store.find_one(id="desktop-storage-state")
            ),
            "projects": {
                state.project_id: dump_to_dict(state)
                for state in self._config_store.find(type=ProjectStorageState)
            },
        }

    def register_close_callback(
        self, close: Callable[[], None], project_id: str | None = None
    ) -> Callable[[], None]:
        """Register when a connection starts; return a function to unregister it.

        The callback runs on project unload or DSS shutdown. Without a project
        ID it runs only on DSS shutdown. Registration after closing is refused.
        """
        if self.closing:
            raise StorageClosingError("Desktop storage is closing")
        close_callbacks = (
            self._close_callbacks
            if project_id is None
            else self._require_open_project(project_id).close_callbacks
        )
        close_callbacks.add(close)
        return lambda: close_callbacks.discard(close)

    @staticmethod
    def _run_close_callbacks(close_callbacks: set[Callable[[], None]]) -> None:
        for close in list(close_callbacks):
            try:
                close()
            except Exception:
                log.exception("Failed to run desktop close callback")
        close_callbacks.clear()

    def begin_closing(self) -> None:
        """Close admission and streams before uvicorn waits for requests."""
        self.closing = True
        self._publish_app_state()
        self._run_close_callbacks(self._close_callbacks)
        for project in self._projects.values():
            self._end_project_streams(project)

    def _end_project_streams(self, project: _Project) -> None:
        self._run_close_callbacks(project.close_callbacks)
        if project.pfm is not None:
            project.pfm.fs_watcher.close_stream()

    @property
    def config_sync_service(self) -> WebSocketSyncService:
        return self._config_sync_service

    @property
    def config_store(self) -> InMemoryStore:
        return self._config_store

    def _resolve_project_path(self, project_id: str) -> Path | None:
        """Resolve a project ID to its repo root path."""
        project = self._projects.get(project_id)
        return project.root if project is not None and project.pfm is not None else None

    def _on_config_changes(self, delta: Delta, origin: str | None = None) -> None:
        """Chained config store callback: persist to disk + react to settings."""
        if origin == "remote" and any(
            is_service_state_id(change.entity_id)
            or change.forward_component.get("type_name")
            in {"DesktopStorageState", "ProjectStorageState"}
            for change in delta.changes()
        ):
            raise ValueError("Backend service state is read-only")
        self._config_file_manager.on_changes(delta, origin)
        self._apply_backup_settings_from_delta(delta)

    def _apply_backup_settings_from_delta(self, delta: Delta) -> None:
        """Check if any ProjectProperties changed and update backup_service.backups_enabled."""
        for change in delta.changes():
            entity_id = change.entity_id
            if not entity_id.startswith("project-props-"):
                continue
            project_id = entity_id.removeprefix("project-props-")
            project = self._projects.get(project_id)
            if project is None or project.pfm is None or project.state == "closing":
                continue
            pfm = project.pfm
            # Read the current entity from the store
            entity = self._config_store.find_one(id=entity_id)
            if entity is not None and isinstance(entity, ProjectProperties):
                try:
                    pfm.backup_service.backups_enabled = entity.backups_enabled
                    project.backup_error = None
                except Exception as exc:
                    project.backup_error = f"Backup service toggle failed: {exc}"
                    log.error(project.backup_error)
                self._publish_project_state(project_id)

    async def load_project(self, project_id: str, repo_root: Path) -> None:
        """Scan the project in a worker, then build it on the loop.

        Concurrent calls share one load task, which a cancelled request doesn't stop.
        """
        if not repo_root.is_absolute():
            raise ValueError("repo_root must be an absolute path")
        if self.closing:
            raise StorageClosingError("Desktop storage is closing")
        project = self._projects.get(project_id)
        if project is not None:
            if project.state == "closing":
                raise StorageClosingError(f"Desktop project '{project_id}' is closing")
            if project.root != repo_root:
                raise ValueError(
                    f"Project '{project_id}' is already loaded at another path"
                )
        else:
            project = _Project(repo_root)
            self._projects[project_id] = project
            self._publish_project_state(project_id)
            project.load_task = asyncio.create_task(
                self._load_project(project_id, project)
            )
            project.load_task.add_done_callback(_observe_task)
        assert project.load_task is not None
        await asyncio.shield(project.load_task)
        # An unload may have begun while the scan was running.
        if project.state == "closing":
            raise StorageClosingError(f"Desktop project '{project_id}' is closing")
        self._require_open_project(project_id)

    async def _load_project(self, project_id: str, project: _Project) -> None:
        try:
            snapshot = await asyncio.to_thread(scan_project, project_id, project.root)
            if project.state == "closing" or self.closing:
                return
            project.pfm = ProjectFolderManager(
                project_id,
                project.root,
                snapshot,
                on_state_changed=lambda: self._publish_project_state(project_id),
            )
            project.history = FullChangeHistoryService(
                project.root / ".pamet" / "change-history.db"
            )
            self._load_project_config(project_id, project.pfm)
            project.state = "open"
            self._publish_project_state(project_id)
            log.info("Loaded project %s from %s", project_id, project.root)
        except Exception:
            log.exception("Failed to load project %s", project_id)
            project.state = "closing"
            self._publish_project_state(project_id)
            await self._release_project(project_id, project)
            if project.unload_task is None:
                self._projects.pop(project_id, None)
            raise

    def _load_project_config(self, project_id: str, pfm: ProjectFolderManager) -> None:
        """Initialize config once, inside the owned load task on the loop."""
        self._config_file_manager.load_project_properties(
            self._config_store, project_id
        )
        project_properties_key = ProjectProperties.id_for_project(project_id)
        props = self._config_store.find_one(id=project_properties_key)
        if props is None:
            props = ProjectProperties(
                id=project_properties_key,
                project_id=project_id,
                title=pfm.repo_root.name,
            )
            self._config_store.insert_one(props)

        backups_enabled = True
        if isinstance(props, ProjectProperties):
            backups_enabled = props.backups_enabled
            if not props.home_page_id:
                first_page = next(pfm.store.find(type=Page), None)
                if first_page is not None:
                    props.home_page_id = first_page.id
                    self._config_store.update_one(props)

        backup = pfm.backup_service
        try:
            backup.backups_enabled = backups_enabled
        except Exception as exc:
            msg = f"Backup service failed to start for project {project_id}: {exc}"
            log.error(msg)
            self._projects[project_id].backup_error = msg

    async def unload_project(self, project_id: str) -> None:
        project = self._projects.get(project_id)
        if project is None:
            return
        if project.unload_task is None:
            project.state = "closing"
            self._publish_project_state(project_id)
            self._end_project_streams(project)
            project.unload_task = asyncio.create_task(
                self._unload_project(project_id, project)
            )
            project.unload_task.add_done_callback(_observe_task)
        await asyncio.shield(project.unload_task)

    async def _unload_project(self, project_id: str, project: _Project) -> None:
        try:
            if project.load_task is not None:
                try:
                    await project.load_task
                except Exception:
                    log.exception("Project %s failed to load before unload", project_id)
            await self._release_project(project_id, project)
        finally:
            self._projects.pop(project_id, None)
        log.info("Unloaded project %s", project_id)

    async def _release_project(self, project_id: str, project: _Project) -> None:
        self._end_project_streams(project)
        if project.pending_operations:
            await asyncio.wait(list(project.pending_operations))
        await self._config_file_manager.release_project(project_id)
        pfm, history = project.pfm, project.history
        if pfm is not None:
            try:
                await pfm.stop()
            except Exception:
                log.exception("Failed to stop/flush project %s", project_id)
        if history is not None:
            try:
                await history.close()
            except Exception:
                log.exception("Failed to close history for %s", project_id)
        if pfm is not None:
            try:
                pfm.close()
            except Exception:
                log.exception("Failed to close project %s", project_id)
        project.pfm = None
        project.history = None
        state = self._config_store.find_one(
            id=ProjectStorageState.id_for_project(project_id)
        )
        if state is not None:
            self._config_store.remove_one(state)

    async def close(self) -> None:
        self.begin_closing()
        if self._close_task is None:
            self._close_task = asyncio.create_task(self._close())
            self._close_task.add_done_callback(_observe_task)
        await asyncio.shield(self._close_task)

    async def _close(self) -> None:
        # Includes projects whose scan has not finished yet.
        for project_id in list(self._projects):
            try:
                await self.unload_project(project_id)
            except Exception:
                log.exception("Failed to unload project %s", project_id)
        await self._config_file_manager.close()
        self._config_store.remove_on_changes_callback(self._on_config_changes)

    def project_folder_manager(self, project_id: str) -> ProjectFolderManager:
        pfm = self._require_open_project(project_id).pfm
        assert pfm is not None
        return pfm

    async def save_changes(self, project_id: str, delta_data: dict) -> None:
        """Save a delta. Once admitted, the save finishes before the project unloads."""
        project = self._require_open_project(project_id)
        assert project.pfm is not None
        await self._run_mutation(project, project.pfm.save(delta_data))

    async def add_file(self, project_id: str, rel: str, data: bytes) -> str:
        project = self._require_open_project(project_id)
        assert project.pfm is not None
        return await self._run_mutation(
            project, project.pfm.file_storage.add(rel, data)
        )

    async def remove_file(self, project_id: str, rel: str) -> bool:
        project = self._require_open_project(project_id)
        assert project.pfm is not None
        return await self._run_mutation(
            project, project.pfm.file_storage.remove_by_path(rel)
        )

    async def _run_mutation(
        self, project: _Project, operation: Coroutine[Any, Any, T]
    ) -> T:
        """Own an admitted mutation through completion, despite waiter cancellation.

        The caller checks admission. The operation owns locking and worker
        offloading; this task keeps its disk and loop-owned bookkeeping alive.
        """
        task = asyncio.create_task(operation)
        project.pending_operations.add(task)
        task.add_done_callback(project.pending_operations.discard)
        task.add_done_callback(_observe_task)
        return await asyncio.shield(task)
