from __future__ import annotations

import hmac
import json
import re
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname

from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.responses import FileResponse, StreamingResponse
from fusion.libs.command import get_command
from fusion.libs.model import dump_to_dict
from fusion.logging import get_logger
from starlette.websockets import WebSocket, WebSocketDisconnect

import pamet
from pamet.services.desktop_storage_service import ProjectNotLoadedError
from pamet.storage.service_utils import ProjectTooLargeError

log = get_logger(__name__)

desktop_router = APIRouter()


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


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
        provided = _extract_bearer_token(request.headers.get("Authorization"))
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
def load_project(project_id: str, payload: dict | None = Body(default=None)):
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

        storage_service.load_project(project_id, repo_root=repo_root)
    except ValueError as exc:
        log.error("Bridge load_project failed: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ProjectTooLargeError as exc:
        log.error("Bridge load_project failed (too large): %s", exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
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
    """WebSocket endpoint for bidirectional config store sync.

    Auth: bearer token passed as ?token= query param (WebSocket
    doesn't support custom headers during the handshake).
    """
    # --- Auth ---
    expected_token = getattr(ws.app.state, "desktop_access_token", None)
    if expected_token:
        provided = ws.query_params.get("token")
        if not provided or not hmac.compare_digest(provided, expected_token):
            await ws.close(code=4401, reason="Unauthorized")
            return

    await ws.accept()

    dss = pamet.desktop_storage_service()
    sync = dss.config_sync_service

    async def send(msg: dict) -> None:
        await ws.send_json(msg)

    async def receive() -> dict:
        return await ws.receive_json()

    try:
        await sync.run(send, receive)
    except WebSocketDisconnect:
        log.info("Config store WS client disconnected")
    except Exception as exc:
        log.error("Config store WS error: %s", exc)


@desktop_router.get("/")
def serve_index(request: Request):
    static_root = getattr(request.app.state, "web_app_static_build_path", None)
    if static_root is None:
        raise HTTPException(status_code=404, detail="No static app configured")
    index_path = static_root / "index.html"
    return FileResponse(index_path)


@desktop_router.get("/static/{path:path}")
def serve_static(path: str, request: Request):
    static_root = getattr(request.app.state, "web_app_static_build_path", None)
    if static_root is None:
        raise HTTPException(status_code=404, detail="No static app configured")
    static_path = (static_root / "static" / path).resolve()
    if not static_path.is_relative_to(static_root):
        raise HTTPException(status_code=400, detail="Invalid path")
    return FileResponse(static_path)


@desktop_router.get("/{user_id}/{project_id}")
def serve_project_index(user_id: str, project_id: str, request: Request):
    _ = user_id
    _ = project_id
    static_root = getattr(request.app.state, "web_app_static_build_path", None)
    if static_root is None:
        raise HTTPException(status_code=404, detail="No static app configured")
    index_path = static_root / "index.html"
    return FileResponse(index_path)


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


@desktop_router.post(
    "/desktop/projects/{project_id}/files/{file_item_id}",
    dependencies=[Depends(require_desktop_auth)],
)
async def upload_file(
    project_id: str,
    file_item_id: str,
    content_hash: str = Form(...),
    path: str = Form(...),
    file: UploadFile = File(...),
):
    _validate_id(file_item_id, "file_item_id")
    _validate_id(content_hash, "content_hash")
    raw = path.strip()
    if not raw:
        raise HTTPException(status_code=400, detail="File path is required")
    rel = PurePosixPath(raw)
    if rel.is_absolute() or ".." in rel.parts:
        raise HTTPException(status_code=400, detail=f"Invalid file path: {path}")

    pfm = _project_runtime(project_id)
    data = await file.read()
    try:
        pfm.file_storage.add(rel, data)
    except (ValueError, FileExistsError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


@desktop_router.get(
    "/desktop/projects/{project_id}/files/{file_item_id}/content",
    dependencies=[Depends(require_desktop_auth)],
)
async def get_file_item_content(
    project_id: str,
    file_item_id: str,
):
    _validate_id(file_item_id, "file_item_id")
    pfm = _project_runtime(project_id)
    path = pfm.file_storage.find_path(file_item_id)
    if path is None:
        raise HTTPException(status_code=404, detail="File item not found")
    return FileResponse(path)


@desktop_router.delete(
    "/desktop/projects/{project_id}/files/{file_item_id}",
    dependencies=[Depends(require_desktop_auth)],
)
async def delete_file_item(
    project_id: str,
    file_item_id: str,
):
    _validate_id(file_item_id, "file_item_id")
    pfm = _project_runtime(project_id)
    deleted = pfm.file_storage.remove(file_item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="File item not found")
    return {"ok": True}
