from __future__ import annotations

import hmac
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from fastapi.responses import FileResponse
from fusion.libs.entity import dump_to_dict
from pamet.services.desktop_storage_service import ProjectNotLoadedError
from pamet.services.rest_api.util import envelope

import pamet


@dataclass
class _DesktopRouteContext:
    commands: dict[str, Callable]
    media_store_path: Path
    web_app_static_build_path: Path | None
    desktop_access_token: str | None


_ctx: _DesktopRouteContext | None = None

router = APIRouter()
media_router = APIRouter(prefix="/media")


def configure_router(
    commands: dict[str, Callable],
    media_store_path: Path,
    web_app_static_build_path: Path | None,
    desktop_access_token: str | None,
):
    global _ctx
    _ctx = _DesktopRouteContext(
        commands=commands,
        media_store_path=media_store_path,
        web_app_static_build_path=web_app_static_build_path,
        desktop_access_token=desktop_access_token,
    )


def get_router() -> APIRouter:
    if _ctx is None:
        raise RuntimeError("Desktop API routers are not configured")
    return router


def get_media_router() -> APIRouter:
    if _ctx is None:
        raise RuntimeError("Desktop API routers are not configured")
    return media_router


def _require_ctx() -> _DesktopRouteContext:
    if _ctx is None:
        raise RuntimeError("Desktop API router is not configured")
    return _ctx


def _extract_bearer_token(auth_header: str | None) -> str | None:
    if not auth_header:
        return None
    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() != "bearer":
        return None
    token = token.strip()
    return token or None


def _is_valid_desktop_token(token: str | None) -> bool:
    expected_token = _require_ctx().desktop_access_token
    if expected_token is None:
        return True
    if not token:
        return False
    return hmac.compare_digest(token, expected_token)


def require_desktop_auth(request: Request):
    if _ctx is None:
        raise RuntimeError("Desktop API router is not configured")
    expected_token = _ctx.desktop_access_token
    if expected_token:
        provided = _extract_bearer_token(request.headers.get("Authorization"))
        if not _is_valid_desktop_token(provided):
            raise HTTPException(
                status_code=401,
                detail="Unauthorized",
                headers={"WWW-Authenticate": "Bearer"},
            )


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


@router.post("/commands/{command_name}/")
def run_command(command_name: str):
    commands = _require_ctx().commands
    if command_name in commands:
        commands[command_name]()


@router.get("/version")
def version():
    return envelope(pamet.__version__)


@router.post(
    "/desktop/storage/project/{project_id}/load",
    dependencies=[Depends(require_desktop_auth)],
)
def load_project(project_id: str, payload: dict | None = Body(default=None)):
    if not project_id:
        raise HTTPException(status_code=400, detail="projectId is required")
    storage_service = pamet.desktop_storage_service()
    try:
        if not isinstance(payload, dict):
            raise ValueError("project load payload must be an object")
        project_uri = payload.get("uri")
        if not isinstance(project_uri, str):
            raise ValueError("project uri must be a string")
        storage_service.load_project(project_id, project_uri=project_uri)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return envelope({"ok": True})


@router.post(
    "/desktop/storage/project/{project_id}/unload",
    dependencies=[Depends(require_desktop_auth)],
)
def unload_project(project_id: str):
    if not project_id:
        raise HTTPException(status_code=400, detail="projectId is required")
    storage_service = pamet.desktop_storage_service()
    storage_service.unload_project(project_id)
    return envelope({"ok": True})


@router.get(
    "/desktop/settings/user",
    dependencies=[Depends(require_desktop_auth)],
)
def get_desktop_user_settings(response: Response):
    _set_no_cache_headers(response)
    return envelope(pamet.desktop_app.get_user_settings())


@router.put(
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


@router.get(
    "/desktop/storage/project/{project_id}/properties",
    dependencies=[Depends(require_desktop_auth)],
)
def get_project_properties(project_id: str, response: Response):
    if not project_id:
        raise HTTPException(status_code=400, detail="projectId is required")
    _set_no_cache_headers(response)
    return envelope(_project_runtime(project_id).get_project_properties())


@router.put(
    "/desktop/storage/project/{project_id}/properties",
    dependencies=[Depends(require_desktop_auth)],
)
def set_project_properties(project_id: str, payload: dict):
    if not project_id:
        raise HTTPException(status_code=400, detail="projectId is required")
    runtime = _project_runtime(project_id)
    runtime.set_project_properties(payload)
    return envelope(runtime.get_project_properties())


@router.get("/")
def serve_index():
    static_root = _require_ctx().web_app_static_build_path
    if static_root is None:
        raise HTTPException(status_code=404, detail="No static app configured")
    index_path = static_root / "index.html"
    return FileResponse(index_path)


@router.get("/static/{path:path}")
def serve_static(path: str):
    static_root = _require_ctx().web_app_static_build_path
    if static_root is None:
        raise HTTPException(status_code=404, detail="No static app configured")
    static_path = static_root / "static" / path
    return FileResponse(static_path)


@router.get("/{user_id}/{project_id}")
def serve_project_index(user_id: str, project_id: str):
    _ = user_id
    _ = project_id
    static_root = _require_ctx().web_app_static_build_path
    if static_root is None:
        raise HTTPException(status_code=404, detail="No static app configured")
    index_path = static_root / "index.html"
    return FileResponse(index_path)


@router.get("/pages")
def get_pages(response: Response):
    pages = [dump_to_dict(page) for page in pamet.pages()]
    _set_no_cache_headers(response)
    return envelope(pages)


@router.get("/p/{page_id}/children")
def get_children(page_id: str, response: Response):
    page = pamet.page(page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    notes = [dump_to_dict(note) for note in pamet.notes(page_id)]
    arrows = [dump_to_dict(arrow) for arrow in pamet.arrows(page_id)]
    _set_no_cache_headers(response)
    return envelope({"notes": notes, "arrows": arrows})


@router.get(
    "/desktop/storage/project/{project_id}/commit-graph",
    dependencies=[Depends(require_desktop_auth)],
)
def get_commit_graph(project_id: str, response: Response, branch: str = "main"):
    runtime = _project_runtime(project_id)
    try:
        commit_graph = runtime.get_commit_graph(branch_name=branch)
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    _set_no_cache_headers(response)
    return commit_graph


@router.get(
    "/desktop/storage/project/{project_id}/commits",
    dependencies=[Depends(require_desktop_auth)],
)
def get_commits(
    project_id: str,
    response: Response,
    ids: list[str] = Query(default=[]),
    branch: str = "main",
):
    runtime = _project_runtime(project_id)
    try:
        commits = runtime.get_commits(ids=ids, branch_name=branch)
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    _set_no_cache_headers(response)
    return commits


@router.post(
    "/desktop/storage/project/{project_id}/repo-update",
    dependencies=[Depends(require_desktop_auth)],
)
def apply_repo_update(project_id: str, payload: dict):
    runtime = _project_runtime(project_id)
    try:
        runtime.apply_repo_update(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    return envelope({"ok": True})


@router.get(
    "/desktop/storage/project/{project_id}/fs-sync/pending-delta",
    dependencies=[Depends(require_desktop_auth)],
)
def get_pending_delta(
    project_id: str,
    response: Response,
    timeout_ms: int = Query(default=0, alias="timeoutMs"),
):
    _ = timeout_ms
    runtime = _project_runtime(project_id)
    try:
        pending_delta = runtime.get_pending_delta()
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    _set_no_cache_headers(response)
    return envelope({"pendingDelta": pending_delta})


@router.get(
    "/desktop/fs/{path:path}",
    dependencies=[Depends(require_desktop_auth)],
)
def get_file(path: str):
    file_path = Path("/") / path
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)


@router.get("/p/{page_id}/media/{path:path}")
def get_media(page_id: str, path: str):
    file_path = _require_ctx().media_store_path / page_id / path
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)


@media_router.post(
    "/item/{media_id}/{content_hash}",
    dependencies=[Depends(require_desktop_auth)],
)
async def upload_media(
    media_id: str,
    content_hash: str,
    project_id: str = Query(..., alias="projectId"),
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
    project_id: str = Query(..., alias="projectId"),
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
    project_id: str = Query(..., alias="projectId"),
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
    project_id: str = Query(..., alias="projectId"),
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
async def clean_trash(project_id: str = Query(..., alias="projectId")):
    media_backend = _project_runtime(project_id).blob_storage_adapter
    removed = media_backend.clean_trash()
    return {"data": {"removed": removed}}
