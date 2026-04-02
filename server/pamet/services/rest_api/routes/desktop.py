from __future__ import annotations

import hmac
from pathlib import Path

from fastapi import (APIRouter, Body, Depends, File, Form, HTTPException,
                     Query, Request, Response, UploadFile)
from fastapi.responses import FileResponse
from fusion.logging import get_logger

import pamet
from pamet.services.desktop_storage_service import ProjectNotLoadedError
from pamet.services.rest_api.util import envelope

log = get_logger(__name__)

desktop_router = APIRouter()
media_router = APIRouter(prefix="/media")


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

def _set_no_cache_headers(response: Response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"


def _project_runtime(project_id: str):
    if not project_id:
        raise HTTPException(status_code=400, detail="projectId is required")
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

@desktop_router.post("/commands/{command_name}/")
def run_command(command_name: str, request: Request):
    commands: dict = getattr(request.app.state, "commands", {})
    if command_name in commands:
        commands[command_name]()


# ---------------------------------------------------------------------------
# Project lifecycle
# ---------------------------------------------------------------------------

@desktop_router.put(
    "/desktop/projects/{project_id}/bridge",
    dependencies=[Depends(require_desktop_auth)],
)
def load_project(project_id: str, payload: dict | None = Body(default=None)):
    if not project_id:
        raise HTTPException(status_code=400, detail="projectId is required")
    storage_service = pamet.desktop_storage_service()
    try:
        if not isinstance(payload, dict):
            raise ValueError(
                f"project load payload must be an object, got: {payload!r}"
            )
        project_uri = payload.get("uri")
        if not isinstance(project_uri, str):
            raise ValueError(f"project uri must be a string, got: {project_uri!r}")
        storage_service.load_project(project_id, project_uri=project_uri)
    except ValueError as exc:
        log.error("Bridge load_project failed: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return envelope({"ok": True})


@desktop_router.delete(
    "/desktop/projects/{project_id}/bridge",
    dependencies=[Depends(require_desktop_auth)],
)
def unload_project(project_id: str):
    if not project_id:
        raise HTTPException(status_code=400, detail="projectId is required")
    storage_service = pamet.desktop_storage_service()
    storage_service.unload_project(project_id)
    return envelope({"ok": True})


@desktop_router.get(
    "/desktop/settings/user",
    dependencies=[Depends(require_desktop_auth)],
)
def get_desktop_user_settings(response: Response):
    _set_no_cache_headers(response)
    return envelope(pamet.desktop_app.get_user_settings())


@desktop_router.put(
    "/desktop/settings/user",
    dependencies=[Depends(require_desktop_auth)],
)
def set_desktop_user_settings(payload: dict | None = Body(default=None)):
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=400, detail="user settings payload must be an object"
        )
    pamet.desktop_app.save_user_settings(payload)
    return envelope({"ok": True})


@desktop_router.get(
    "/desktop/projects/{project_id}/properties",
    dependencies=[Depends(require_desktop_auth)],
)
def get_project_properties(project_id: str, response: Response):
    if not project_id:
        raise HTTPException(status_code=400, detail="projectId is required")
    _set_no_cache_headers(response)
    return envelope(_project_runtime(project_id).get_project_properties())


@desktop_router.put(
    "/desktop/projects/{project_id}/properties",
    dependencies=[Depends(require_desktop_auth)],
)
def set_project_properties(project_id: str, payload: dict):
    if not project_id:
        raise HTTPException(status_code=400, detail="projectId is required")
    runtime = _project_runtime(project_id)
    runtime.set_project_properties(payload)
    return envelope(runtime.get_project_properties())


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
    "/desktop/projects/{project_id}/changes/pending",
    dependencies=[Depends(require_desktop_auth)],
)
def get_pending_delta(
    project_id: str,
    response: Response,
    timeout_ms: int = Query(default=0),
):
    runtime = _project_runtime(project_id)
    try:
        pending_delta = runtime.get_pending_delta(timeout_ms)
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    _set_no_cache_headers(response)
    return envelope({"pendingDelta": pending_delta})


@desktop_router.get(
    "/desktop/projects/{project_id}/entities",
    dependencies=[Depends(require_desktop_auth)],
)
def find_entities(project_id: str, response: Response):
    runtime = _project_runtime(project_id)
    try:
        entities = runtime.find_entities()
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    _set_no_cache_headers(response)
    return envelope({"entities": entities})


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
    snapshot_hash = payload.get("snapshotHash")
    runtime.apply_delta(delta_data, snapshot_hash=snapshot_hash)
    return envelope({"ok": True})


@media_router.post(
    "/item/{media_id}/{content_hash}",
    dependencies=[Depends(require_desktop_auth)],
)
async def upload_media(
    media_id: str,
    content_hash: str,
    project_id: str = Query(...),
    path: str = Form(...),
    file: UploadFile = File(...),
):
    media_backend = _project_runtime(project_id).blob_storage_adapter
    data = await file.read()
    try:
        media_backend.save_bytes(media_id, content_hash, path, data, file.content_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"data": {"ok": True}}


@media_router.get(
    "/item/{media_id}/{content_hash}",
    dependencies=[Depends(require_desktop_auth)],
)
async def get_media_item(
    media_id: str,
    content_hash: str,
    project_id: str = Query(...),
):
    media_backend = _project_runtime(project_id).blob_storage_adapter
    path = media_backend.find_item_path(media_id, content_hash)
    if path is None:
        raise HTTPException(status_code=404, detail="Media not found")
    return FileResponse(path)


@media_router.delete(
    "/item/{media_id}/{content_hash}",
    dependencies=[Depends(require_desktop_auth)],
)
async def delete_media(
    media_id: str,
    content_hash: str,
    project_id: str = Query(...),
):
    media_backend = _project_runtime(project_id).blob_storage_adapter
    moved = media_backend.move_to_trash(media_id, content_hash)
    if moved:
        return {"data": {"ok": True}}
    return {"data": {"ok": False, "reason": "not_found"}}


@media_router.post(
    "/item/{media_id}/{content_hash}/restore",
    dependencies=[Depends(require_desktop_auth)],
)
async def restore_media(
    media_id: str,
    content_hash: str,
    project_id: str = Query(...),
):
    media_backend = _project_runtime(project_id).blob_storage_adapter
    restored = media_backend.restore_from_trash(media_id, content_hash)
    if restored:
        return {"data": {"ok": True}}
    return {"data": {"ok": False, "reason": "not_in_trash"}}


@media_router.post(
    "/trash/clean",
    dependencies=[Depends(require_desktop_auth)],
)
async def clean_trash(project_id: str = Query(...)):
    media_backend = _project_runtime(project_id).blob_storage_adapter
    removed = media_backend.clean_trash()
    return {"data": {"removed": removed}}
