from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal, TypeVar

from sivkit.storage.delta import Delta
from sivkit.storage.in_memory_store import InMemoryStore
from sivkit.storage.websocket_sync_service import WebSocketSyncService

from pamet.model.config import ProjectProperties
from pamet.model.page import Page
from pamet.services.config_file_manager import ConfigFileManager, DSSStatus
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

    def project_problems(self) -> dict[str, list[dict]]:
        """Problems of each open project, as listed in ``/status``."""
        return {
            project_id: [asdict(problem) for problem in project.pfm.problems.values()]
            for project_id, project in self._projects.items()
            if project.state == "open" and project.pfm is not None
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
        if origin == "remote":
            entity_ids = [c.entity_id for c in delta.changes()]
            log.warning(
                "_on_config_changes: REMOTE delta from client! entities=%s",
                entity_ids,
            )
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
            project.pfm = ProjectFolderManager(project_id, project.root, snapshot)
            project.history = FullChangeHistoryService(
                project.root / ".pamet" / "change-history.db"
            )
            self._load_project_config(project_id, project.pfm)
            project.state = "open"
            log.info("Loaded project %s from %s", project_id, project.root)
        except Exception:
            log.exception("Failed to load project %s", project_id)
            project.state = "closing"
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
            self.status["errors"].setdefault("backup_service", {})[project_id] = msg

        self.status["backup_service"][project_id] = {
            "present": True,
            "backups_enabled": backup.backups_enabled,
            "backup_folder": str(backup.backup_folder),
        }

    async def unload_project(self, project_id: str) -> None:
        project = self._projects.get(project_id)
        if project is None:
            return
        if project.unload_task is None:
            project.state = "closing"
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
        self.status["backup_service"].pop(project_id, None)

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
