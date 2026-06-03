from __future__ import annotations

import asyncio
import hmac
import json
import logging
import re
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
from sivkit.libs.command import get_command
from sivkit.libs.model import dump_to_dict
from sivkit.storage.starlette_sync import StarletteSyncEndpoint
from starlette.websockets import WebSocket

import pamet
from pamet.services.desktop_storage_service import ProjectNotLoadedError
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


def require_desktop_auth(request: Request):
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
def get_version():
    return {"data": pamet.__version__}


@desktop_router.get("/status", dependencies=[Depends(require_desktop_auth)])
def get_status():
    dss = pamet.desktop_storage_service()
    return dss.status


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
def run_public_command(command_name: str, payload: dict | None = Body(default=None)):
    if command_name not in PUBLIC_COMMAND_NAMES:
        raise HTTPException(
            status_code=403, detail=f"Command not public: {command_name}"
        )
    return _run_command(command_name, payload)


@desktop_router.post(
    "/desktop/gui/commands/{command_name}/",
    dependencies=[Depends(require_desktop_auth)],
)
def run_gui_command(command_name: str, payload: dict | None = Body(default=None)):
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

        # 1. Blocking I/O in a thread (read .canvas files)
        await asyncio.to_thread(storage_service.load_project_fs, project_id, repo_root)
    except ValueError as exc:
        log.error("Bridge load_project failed: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ProjectTooLargeError as exc:
        log.error("Bridge load_project failed (too large): %s", exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # 2. Config store update on the event loop (fires push_delta)
    log.info("bridge load_project: calling load_project_config for %s", project_id)
    storage_service.load_project_config(project_id)

    # 3. Wait for the config delta to be delivered to the client
    future = storage_service.config_sync_service.last_push_future
    if future is not None:
        await future
    log.info(
        "bridge load_project: config sync complete for %s, returning 200", project_id
    )
    return {"ok": True}


@desktop_router.delete(
    "/desktop/projects/{project_id}/bridge",
    dependencies=[Depends(require_desktop_auth)],
)
def unload_project(project_id: str):
    _validate_id(project_id, "project_id")
    storage_service = pamet.desktop_storage_service()
    storage_service.unload_project(project_id)
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
    endpoint = StarletteSyncEndpoint(sync_service=dss.config_sync_service)
    await endpoint.serve(ws)
    log.info("Config store WS client disconnected")


@desktop_router.websocket("/desktop/projects/{project_id}/changes/history/ws")
async def change_history_ws(ws: WebSocket, project_id: str):
    """WebSocket endpoint for full change history streaming.

    The frontend connects as *authority* and streams deltas for each
    user action.  The backend (receiver) commits them to a SQLite repo.
    """
    # --- Auth ---
    expected_token = getattr(ws.app.state, "desktop_access_token", None)
    if expected_token:
        provided = ws.cookies.get(DESKTOP_AUTH_COOKIE_NAME)
        if not provided or not hmac.compare_digest(provided, expected_token):
            log.warning(
                "Change history WS auth failed for project %s: cookie %s, expected_token set=%s",
                project_id,
                "present" if provided else "MISSING",
                bool(expected_token),
            )
            await ws.close(code=4401, reason="Unauthorized")
            return

    dss = pamet.desktop_storage_service()
    svc = dss.change_history_service(project_id)
    if svc is None:
        registered = list(dss._change_history_services.keys())
        log.warning(
            "Change history WS: service is None for project %s. "
            "Registered services: %s",
            project_id,
            registered,
        )
        await ws.close(code=4503, reason="Change history not enabled for this project")
        return

    if not svc.is_healthy:
        await ws.close(code=4503, reason=f"Change history degraded: {svc.error}")
        return

    log.info("Change history WS auth OK for project %s", project_id)
    endpoint = StarletteSyncEndpoint(sync_service=svc.ws_sync_service)
    await endpoint.serve(ws)
    log.info("Change history WS client disconnected (project %s)", project_id)


# ---------------------------------------------------------------------------
# Change-history VCS read endpoints (used by replay)
# ---------------------------------------------------------------------------


@desktop_router.get("/desktop/projects/{project_id}/changes/history/branches")
def change_history_branches(
    project_id: str,
    request: Request,
    _user: str = Depends(require_desktop_auth),
):
    """Return branch metadata for the change-history repository."""
    dss = pamet.desktop_storage_service()
    svc = dss.change_history_service(project_id)
    if svc is None:
        raise HTTPException(
            status_code=404,
            detail="Change history not enabled for this project",
        )
    if not svc.is_healthy:
        raise HTTPException(
            status_code=503, detail=f"Change history degraded: {svc.error}"
        )

    repo = svc.repository
    graph = repo.get_commit_graph()
    return [b.asdict() for b in graph.branches()]


@desktop_router.get("/desktop/projects/{project_id}/changes/history/commit-graph")
def change_history_commit_graph(
    project_id: str,
    request: Request,
    branch: str = "main",
    _user: str = Depends(require_desktop_auth),
):
    """Return the commit graph (branch metadata + commit metadata without
    delta_data) for the change-history repository.

    Returns ``{"branches": [...], "commits": [...]}``.
    """
    dss = pamet.desktop_storage_service()
    svc = dss.change_history_service(project_id)
    if svc is None:
        raise HTTPException(
            status_code=404,
            detail="Change history not enabled for this project",
        )
    if not svc.is_healthy:
        raise HTTPException(
            status_code=503, detail=f"Change history degraded: {svc.error}"
        )

    repo = svc.repository
    graph = repo.get_commit_graph()
    return graph.data().__dict__


@desktop_router.get("/desktop/projects/{project_id}/changes/history/commits")
def change_history_commits(
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
    dss = pamet.desktop_storage_service()
    svc = dss.change_history_service(project_id)
    if svc is None:
        raise HTTPException(
            status_code=404,
            detail="Change history not enabled for this project",
        )
    if not svc.is_healthy:
        raise HTTPException(
            status_code=503, detail=f"Change history degraded: {svc.error}"
        )

    repo = svc.repository

    # Mode 1: fetch by IDs
    if ids:
        full_commits = repo.get_commits(ids)
        return [c.asdict() for c in full_commits]

    # Mode 2: paginated walk
    count = min(max(count, 1), 500)

    graph = repo.get_commit_graph()
    all_branch_commits = graph.branch_commits(branch)  # chronological

    # Find start position
    start_idx = 0
    if from_id:
        for i, cm in enumerate(all_branch_commits):
            if cm.id == from_id:
                start_idx = i + 1  # exclusive — start after from_id
                break
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Commit {from_id} not found on branch {branch}",
            )

    selected_meta = all_branch_commits[start_idx : start_idx + count]
    has_more = (start_idx + count) < len(all_branch_commits)

    # Fetch full commits (with delta_data) from the repo
    if selected_meta:
        full_commits = repo.get_commits([cm.id for cm in selected_meta])
        result = [c.asdict() for c in full_commits]
    else:
        result = []

    return {"commits": result, "has_more": has_more}


# ---------------------------------------------------------------------------
# Change-history VCS integrity endpoints
# ---------------------------------------------------------------------------


def _write_integrity_log(svc, operation: str, data: dict) -> str:
    """Write a JSON diagnostics log file, open it, and return its absolute path."""
    from datetime import datetime

    import sivkit
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = svc.diagnostics_dir / f"integrity-{operation}-{ts}.json"
    log_path.write_text(json.dumps(data, indent=2, default=str))

    # Open the file on the main thread (server runs in a background thread)
    path_str = str(log_path.resolve())
    sivkit.call_delayed(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(path_str)))

    return path_str


@desktop_router.post(
    "/desktop/projects/{project_id}/changes/history/check-all",
    dependencies=[Depends(require_desktop_auth)],
)
async def change_history_check_all(project_id: str):
    """Linear replay checking all stored hashes. Streams progress via SSE."""
    from sivkit.storage.vcs_diagnostics import verify_or_fix_hashes

    dss = pamet.desktop_storage_service()
    svc = dss.change_history_service(project_id)
    if svc is None:
        raise HTTPException(
            status_code=404,
            detail="Change history not enabled for this project",
        )

    if not svc.integrity_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=409, detail="An integrity operation is already running"
        )

    def _sse_generator():
        try:
            mismatches = 0
            total = 0
            mismatch_commits = []
            for progress in verify_or_fix_hashes(svc.adapter, "main", fix=False):
                total = progress.total_commits
                if progress.status == "mismatch_reported":
                    mismatches += 1
                    mismatch_commits.append(
                        {
                            "index": progress.commit_index,
                            "commit_id": progress.commit_id,
                            "computed_hash": progress.computed_hash,
                            "stored_hash": progress.stored_hash,
                            "delta_data": progress.delta_data,
                            "parent_id": progress.parent_id,
                            "timestamp": progress.timestamp,
                            "message": progress.message,
                        }
                    )
                yield f"data: {json.dumps({'type': 'progress', 'index': progress.commit_index, 'total': progress.total_commits, 'status': progress.status, 'commit_id': progress.commit_id, 'computed_hash': progress.computed_hash, 'stored_hash': progress.stored_hash})}\n\n"
            log_data = {
                "total": total,
                "mismatches": mismatches,
                "mismatch_commits": mismatch_commits,
            }
            yield f"data: {json.dumps({'type': 'done', 'total': total, 'mismatches': mismatches, 'log_path': _write_integrity_log(svc, 'check-all', log_data)})}\n\n"
        finally:
            svc.integrity_lock.release()

    return StreamingResponse(
        _sse_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@desktop_router.post(
    "/desktop/projects/{project_id}/changes/history/repair-hashes",
    dependencies=[Depends(require_desktop_auth)],
)
async def change_history_repair_hashes(project_id: str):
    """Linear replay fixing all mismatched hashes. Streams progress via SSE."""
    from sivkit.storage.vcs_diagnostics import verify_or_fix_hashes

    dss = pamet.desktop_storage_service()
    svc = dss.change_history_service(project_id)
    if svc is None:
        raise HTTPException(
            status_code=404,
            detail="Change history not enabled for this project",
        )

    if not svc.integrity_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=409, detail="An integrity operation is already running"
        )

    def _sse_generator():
        try:
            fixed = 0
            total = 0
            mismatch_commits = []
            for progress in verify_or_fix_hashes(svc.adapter, "main", fix=True):
                total = progress.total_commits
                if progress.status == "mismatch_fixed":
                    fixed += 1
                    mismatch_commits.append(
                        {
                            "index": progress.commit_index,
                            "commit_id": progress.commit_id,
                            "computed_hash": progress.computed_hash,
                            "stored_hash": progress.stored_hash,
                            "delta_data": progress.delta_data,
                            "parent_id": progress.parent_id,
                            "timestamp": progress.timestamp,
                            "message": progress.message,
                        }
                    )
                yield f"data: {json.dumps({'type': 'progress', 'index': progress.commit_index, 'total': progress.total_commits, 'status': progress.status, 'commit_id': progress.commit_id})}\n\n"

            # Attempt to recover the service after repair
            recovery_error = None
            if fixed > 0 and not svc.is_healthy:
                try:
                    svc.retry_hydration()
                except Exception as exc:
                    recovery_error = str(exc)

            # Clear the status error if service recovered
            if svc.is_healthy:
                ch_errors = dss.status.get("errors", {}).get("change_history")
                if ch_errors and project_id in ch_errors:
                    del ch_errors[project_id]

            log_data = {
                "total": total,
                "fixed": fixed,
                "recovered": svc.is_healthy,
                "recovery_error": recovery_error,
                "mismatch_commits": mismatch_commits,
            }
            log_path = _write_integrity_log(svc, "repair-hashes", log_data)
            yield f"data: {json.dumps({'type': 'done', 'total': total, 'fixed': fixed, 'recovered': svc.is_healthy, 'recovery_error': recovery_error, 'log_path': log_path})}\n\n"
        finally:
            svc.integrity_lock.release()

    return StreamingResponse(
        _sse_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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
def find_entities(project_id: str):
    runtime = _project_runtime(project_id)
    entities = [dump_to_dict(e) for e in runtime.store.find()]
    return {"entities": entities}


@desktop_router.post(
    "/desktop/projects/{project_id}/changes",
    dependencies=[Depends(require_desktop_auth)],
)
def apply_changes(project_id: str, payload: dict = Body(...)):
    runtime = _project_runtime(project_id)
    delta_data = payload.get("delta")
    if not delta_data or not isinstance(delta_data, dict):
        raise HTTPException(
            status_code=400, detail="'delta' must be a non-empty object"
        )
    runtime.apply_delta(delta_data)
    return {"ok": True}
