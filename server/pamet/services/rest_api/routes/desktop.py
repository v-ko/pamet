from __future__ import annotations

import asyncio
import hmac
import json
import logging
import re
import threading
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname

from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import FileResponse, StreamingResponse
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from sivkit.libs.command import get_command
from sivkit.libs.model import dump_to_dict
from sivkit.storage.commit import Commit
from sivkit.storage.starlette_sync import StarletteSyncEndpoint
from starlette.websockets import WebSocket

import pamet
from pamet.services.desktop_storage_service import (
    ProjectNotLoadedError,
    StorageClosingError,
)
from pamet.services.full_change_history_service import (
    FullChangeHistoryService,
    HistoryCommitNotFoundError,
    IntegrityRunningError,
    ParentMismatchError,
)
from pamet.storage.project_walk import ProjectTooLargeError

log = logging.getLogger(__name__)

desktop_router = APIRouter()


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


DESKTOP_AUTH_COOKIE_NAME = "pamet_desktop_token"


def _extract_bearer_token(auth_header: str | None) -> str | None:
    if not auth_header:
        return None
    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() != "bearer":
        return None
    token = token.strip()
    return token or None


async def require_desktop_auth(request: Request):
    expected_token = getattr(request.app.state, "desktop_access_token", None)
    if expected_token:
        # Accept Bearer header or auth cookie
        provided = _extract_bearer_token(request.headers.get("Authorization"))
        if not provided:
            provided = request.cookies.get(DESKTOP_AUTH_COOKIE_NAME)
        if not provided or not hmac.compare_digest(provided, expected_token):
            raise HTTPException(
                status_code=401,
                detail="Unauthorized",
                headers={"WWW-Authenticate": "Bearer"},
            )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_ID_RE = re.compile(r"^[a-z0-9-]+$")


def _validate_id(value: str, name: str = "id") -> str:
    """Validate that a path-parameter ID contains only safe characters."""
    if not value or not _VALID_ID_RE.match(value):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {name}: must match [a-z0-9-]+",
        )
    return value


def _project_runtime(project_id: str):
    _validate_id(project_id, "project_id")
    try:
        storage_service = pamet.desktop_storage_service()
        return storage_service.project_folder_manager(project_id)
    except StorageClosingError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ProjectNotLoadedError as exc:
        raise HTTPException(
            status_code=412,
            detail=f"Desktop project session is not loaded for '{project_id}'",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to access desktop project runtime for '{project_id}'",
        ) from exc


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


# Commands accessible without auth (for IPC from other processes)
PUBLIC_COMMAND_NAMES = frozenset(
    {
        "raise_window",
        "grab_screen_snippet",
        "open_backups_folder",
    }
)


@desktop_router.get("/version")
async def get_version():
    return {"data": pamet.__version__}


@desktop_router.get("/status", dependencies=[Depends(require_desktop_auth)])
async def get_status():
    dss = pamet.desktop_storage_service()
    return {**dss.status, "problems": dss.project_problems()}


def _run_command(command_name: str, payload: dict | None):
    cmd = get_command(command_name)
    if cmd is None:
        raise HTTPException(status_code=404, detail=f"Unknown command: {command_name}")
    try:
        if payload:
            cmd(**payload)
        else:
            cmd()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"ok": True}


@desktop_router.post("/desktop/commands/{command_name}/")
async def run_public_command(
    command_name: str, payload: dict | None = Body(default=None)
):
    if command_name not in PUBLIC_COMMAND_NAMES:
        raise HTTPException(
            status_code=403, detail=f"Command not public: {command_name}"
        )
    return _run_command(command_name, payload)


@desktop_router.post(
    "/desktop/gui/commands/{command_name}/",
    dependencies=[Depends(require_desktop_auth)],
)
async def run_gui_command(command_name: str, payload: dict | None = Body(default=None)):
    return _run_command(command_name, payload)


# ---------------------------------------------------------------------------
# Project lifecycle
# ---------------------------------------------------------------------------


@desktop_router.put(
    "/desktop/projects/{project_id}/bridge",
    dependencies=[Depends(require_desktop_auth)],
)
async def load_project(project_id: str, payload: dict | None = Body(default=None)):
    _validate_id(project_id, "project_id")
    storage_service = pamet.desktop_storage_service()
    try:
        if not isinstance(payload, dict):
            raise ValueError(
                f"project load payload must be an object, got: {payload!r}"
            )
        project_uri = payload.get("uri")
        if not isinstance(project_uri, str) or not project_uri.strip():
            raise ValueError(
                f"project uri must be a non-empty string, got: {project_uri!r}"
            )

        parsed = urlparse(project_uri.strip())
        if parsed.scheme != "file":
            raise ValueError("Desktop project URI must use the file scheme")
        if parsed.netloc:
            raise ValueError("Desktop project file URI must not use a remote host")

        repo_root = Path(url2pathname(unquote(parsed.path)))
        if not repo_root.is_absolute():
            raise ValueError(
                "Desktop project file URI must resolve to an absolute path"
            )

        await storage_service.load_project(project_id, repo_root)
    except StorageClosingError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        log.error("Bridge load_project failed: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ProjectTooLargeError as exc:
        log.error("Bridge load_project failed (too large): %s", exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # The client must receive the project's config before the load returns.
    future = storage_service.config_sync_service.last_push_future
    if future is not None:
        await asyncio.shield(future)
    _project_runtime(project_id)
    log.info(
        "bridge load_project: config sync complete for %s, returning 200", project_id
    )
    return {"ok": True}


@desktop_router.delete(
    "/desktop/projects/{project_id}/bridge",
    dependencies=[Depends(require_desktop_auth)],
)
async def unload_project(project_id: str):
    _validate_id(project_id, "project_id")
    storage_service = pamet.desktop_storage_service()
    await storage_service.unload_project(project_id)
    return {"ok": True}


@desktop_router.websocket("/config/store/ws")
async def config_store_ws(ws: WebSocket):
    """WebSocket endpoint for bidirectional config store sync."""
    # --- Auth ---
    expected_token = getattr(ws.app.state, "desktop_access_token", None)
    if expected_token:
        provided = ws.cookies.get(DESKTOP_AUTH_COOKIE_NAME)
        if not provided or not hmac.compare_digest(provided, expected_token):
            log.warning(
                "Config store WS auth failed: cookie %s, expected_token set=%s",
                "present" if provided else "MISSING",
                bool(expected_token),
            )
            await ws.close(code=4401, reason="Unauthorized")
            return

    log.info("Config store WS auth OK")
    dss = pamet.desktop_storage_service()
    if dss.closing:
        await ws.close(code=1001, reason="Desktop storage is closing")
        return
    endpoint = StarletteSyncEndpoint(sync_service=dss.config_sync_service)
    task = asyncio.create_task(endpoint.serve(ws))
    ended_by_storage = False

    def end() -> None:
        nonlocal ended_by_storage
        ended_by_storage = True
        task.cancel()

    remove_close_callback = dss.register_close_callback(end)
    try:
        await task
    except asyncio.CancelledError:
        if not ended_by_storage:
            raise
        await ws.close(code=1001, reason="Desktop storage is closing")
    finally:
        remove_close_callback()
    log.info("Config store WS client disconnected")


# ---------------------------------------------------------------------------
# Change history (written by the storage worker, read by replay)
# ---------------------------------------------------------------------------


def _history_service(project_id: str) -> FullChangeHistoryService:
    _validate_id(project_id, "project_id")
    try:
        return pamet.desktop_storage_service().change_history_service(project_id)
    except StorageClosingError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ProjectNotLoadedError as exc:
        raise HTTPException(
            status_code=412,
            detail=f"Desktop project session is not loaded for '{project_id}'",
        ) from exc


def _set_history_error(project_id: str, message: str | None) -> None:
    errors = pamet.desktop_storage_service().status["errors"]
    if message is None:
        errors.get("change_history", {}).pop(project_id, None)
    else:
        errors.setdefault("change_history", {})[project_id] = message


@desktop_router.post(
    "/desktop/projects/{project_id}/changes/history/commits",
    dependencies=[Depends(require_desktop_auth)],
)
async def change_history_append(project_id: str, payload: dict = Body(...)):
    """Append commits in one transaction; 409 if the first parent isn't the head."""
    history_service = _history_service(project_id)
    try:
        commits = [Commit.from_dict(c) for c in payload["commits"]]
    except (KeyError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=f"Bad commits: {exc}") from exc
    if not commits:
        raise HTTPException(status_code=400, detail="'commits' must not be empty")
    try:
        head_id = await history_service.append(commits)
    except ParentMismatchError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"head_id": head_id}


@desktop_router.post(
    "/desktop/projects/{project_id}/changes/history/check",
    dependencies=[Depends(require_desktop_auth)],
)
async def change_history_verify_and_reconcile(
    project_id: str, payload: dict = Body(...)
):
    """Verify stored hashes and automatically commit any missing project changes."""
    history_service = _history_service(project_id)
    entities = payload.get("entities")
    snapshot_hash = payload.get("snapshot_hash")
    if not isinstance(entities, list) or not isinstance(snapshot_hash, str):
        raise HTTPException(
            status_code=400, detail="Expected 'entities' list and 'snapshot_hash'"
        )
    result = await history_service.verify_and_reconcile(entities, snapshot_hash)
    if result["mismatches"]:
        _set_history_error(
            project_id, f"hash mismatch in {result['mismatches']} history commits"
        )
    elif result["hashes_disagree"]:
        _set_history_error(project_id, "hash mismatch between TS and Python")
    else:
        _set_history_error(project_id, None)
    return result


@desktop_router.get("/desktop/projects/{project_id}/changes/history/branches")
async def change_history_branches(
    project_id: str,
    request: Request,
    _user: str = Depends(require_desktop_auth),
):
    """Return branch metadata for the change-history repository."""
    history_service = _history_service(project_id)
    graph = await history_service.commit_graph()
    return [b.asdict() for b in graph.branches()]


@desktop_router.get("/desktop/projects/{project_id}/changes/history/commit-graph")
async def change_history_commit_graph(
    project_id: str,
    request: Request,
    branch: str = "main",
    _user: str = Depends(require_desktop_auth),
):
    """Return the commit graph (branch metadata + commit metadata without
    delta_data) for the change-history repository.

    Returns ``{"branches": [...], "commits": [...]}``.
    """
    history_service = _history_service(project_id)
    graph = await history_service.commit_graph()
    return graph.data().__dict__


@desktop_router.get("/desktop/projects/{project_id}/changes/history/commits")
async def change_history_commits(
    project_id: str,
    request: Request,
    branch: str = "main",
    from_id: str | None = None,
    count: int = 50,
    ids: list[str] | None = Query(None),
    _user: str = Depends(require_desktop_auth),
):
    """Return commits (with delta_data) from the change-history repository.

    **Mode 1 – by IDs** (when ``ids`` is provided):
    Fetch specific commits by their IDs.  Returns a flat list of commit
    dicts.

    **Mode 2 – paginated walk** (default, when ``ids`` is absent):
    Walk forward along ``branch`` starting after ``from_id``.

    - ``branch``: branch name (default ``main``)
    - ``from_id``: start *after* this commit ID (exclusive). If omitted
      starts from the branch root.
    - ``count``: max number of commits to return (default 50, capped at 500).

    Returns ``{"commits": [...], "has_more": bool}``.
    Each commit dict has: id, parent_id, snapshot_hash, timestamp, message,
    delta_data.
    """
    history_service = _history_service(project_id)

    # Mode 1: fetch by IDs
    if ids:
        full_commits = await history_service.get_commits(ids)
        return [c.asdict() for c in full_commits]

    # Mode 2: paginated walk
    count = min(max(count, 1), 500)

    try:
        commits, has_more = await history_service.get_commits_page(
            branch, from_id, count
        )
    except HistoryCommitNotFoundError as exc:
        raise HTTPException(
            status_code=404, detail=f"Commit {from_id} not found on branch {branch}"
        ) from exc
    return {"commits": [commit.asdict() for commit in commits], "has_more": has_more}


# ---------------------------------------------------------------------------
# Change-history VCS integrity endpoints
# ---------------------------------------------------------------------------


def _start_integrity_run(project_id: str, fix: bool) -> StreamingResponse:
    history_service = _history_service(project_id)
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[dict | None] = asyncio.Queue()
    listening = threading.Event()
    listening.set()

    def deliver(event: dict | None) -> None:
        if listening.is_set():
            queue.put_nowait(event)

    def post(event: dict | None) -> None:
        if listening.is_set():
            loop.call_soon_threadsafe(deliver, event)

    def end_stream() -> None:
        listening.clear()
        queue.put_nowait(None)

    dss = pamet.desktop_storage_service()
    remove_close_callback = dss.register_close_callback(end_stream, project_id)
    try:
        operation = history_service.start_integrity(fix, post)
    except IntegrityRunningError as exc:
        remove_close_callback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    def finished(result: asyncio.Future) -> None:
        try:
            summary = result.result()
            QDesktopServices.openUrl(QUrl.fromLocalFile(summary["log_path"]))
            if fix:
                _set_history_error(project_id, None)
            post({"type": "done", **summary})
        except Exception as exc:
            log.exception("Change history integrity run failed")
            post({"type": "error", "message": str(exc)})
        finally:
            post(None)
            remove_close_callback()

    operation.add_done_callback(finished)

    # A client that disconnects stops the stream, not the run.
    async def _sse_generator():
        try:
            while (event := await queue.get()) is not None:
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            listening.clear()
            remove_close_callback()

    return StreamingResponse(
        _sse_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@desktop_router.post(
    "/desktop/projects/{project_id}/changes/history/check-all",
    dependencies=[Depends(require_desktop_auth)],
)
async def change_history_check_all(project_id: str):
    """Linear replay checking all stored hashes. Streams progress via SSE."""
    return _start_integrity_run(project_id, fix=False)


@desktop_router.post(
    "/desktop/projects/{project_id}/changes/history/repair-hashes",
    dependencies=[Depends(require_desktop_auth)],
)
async def change_history_repair_hashes(project_id: str):
    """Linear replay fixing all mismatched hashes. Streams progress via SSE."""
    return _start_integrity_run(project_id, fix=True)


@desktop_router.get(
    "/{user_id}/{project_id}/files/{file_path:path}",
    dependencies=[Depends(require_desktop_auth)],
)
async def get_file(
    user_id: str,
    project_id: str,
    file_path: str,
):
    _ = user_id
    pfm = _project_runtime(project_id)
    path = pfm.file_storage.get_path(file_path)
    if path is None:
        raise HTTPException(status_code=404, detail="File not found")
    # Vary: Origin prevents the browser from reusing a non-CORS cached response
    # for a CORS request (crossOrigin="use-credentials" on <img> elements).
    return FileResponse(path, headers={"Vary": "Origin"})


@desktop_router.post(
    "/{user_id}/{project_id}/files/{file_path:path}",
    dependencies=[Depends(require_desktop_auth)],
)
async def upload_file(
    user_id: str,
    project_id: str,
    file_path: str,
    file: UploadFile = File(...),
):
    _ = user_id
    raw = file_path.strip()
    if not raw:
        raise HTTPException(status_code=400, detail="File path is required")
    rel = PurePosixPath(raw)
    if rel.is_absolute() or ".." in rel.parts:
        raise HTTPException(status_code=400, detail=f"Invalid file path: {file_path}")

    pfm = _project_runtime(project_id)
    data = await file.read()
    if _project_runtime(project_id) is not pfm:
        raise HTTPException(status_code=409, detail="Desktop project session changed")
    try:
        content_hash = pfm.file_storage.add(rel, data)
    except (ValueError, FileExistsError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "hash": content_hash, "path": raw}


@desktop_router.delete(
    "/{user_id}/{project_id}/files/{file_path:path}",
    dependencies=[Depends(require_desktop_auth)],
)
async def delete_file(
    user_id: str,
    project_id: str,
    file_path: str,
):
    _ = user_id
    pfm = _project_runtime(project_id)
    deleted = pfm.file_storage.remove_by_path(file_path)
    if not deleted:
        raise HTTPException(status_code=404, detail="File not found")
    return {"ok": True}


@desktop_router.get(
    "/desktop/projects/{project_id}/changes/stream",
    dependencies=[Depends(require_desktop_auth)],
)
async def project_changes_stream(project_id: str):
    runtime = _project_runtime(project_id)

    async def _sse_generator():
        async for delta_dict in runtime.fs_watcher.deltas_stream():
            yield f"data: {json.dumps(delta_dict)}\n\n"

    return StreamingResponse(
        _sse_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@desktop_router.get(
    "/desktop/projects/{project_id}/entities",
    dependencies=[Depends(require_desktop_auth)],
)
async def find_entities(project_id: str):
    runtime = _project_runtime(project_id)
    entities = [dump_to_dict(e) for e in runtime.store.find()]
    return {"entities": entities}


@desktop_router.post(
    "/desktop/projects/{project_id}/changes",
    dependencies=[Depends(require_desktop_auth)],
)
async def apply_changes(project_id: str, payload: dict = Body(...)):
    runtime = _project_runtime(project_id)
    delta_data = payload.get("delta")
    if not delta_data or not isinstance(delta_data, dict):
        raise HTTPException(
            status_code=400, detail="'delta' must be a non-empty object"
        )
    runtime.apply_delta(delta_data)
    return {"ok": True}
