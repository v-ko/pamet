from __future__ import annotations
import hmac
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from fastapi.responses import FileResponse
from fusion.libs.entity import dump_to_dict
from pamet.services.media_backend import MediaStorageBackendService
from pamet.services.rest_api.util import envelope

import pamet
from fusion import get_logger
from pamet import desktop_app

log = get_logger(__name__)


@dataclass
class _DesktopRouteContext:
    commands: dict[str, Callable]
    media_store_path: Path
    web_app_static_build_path: Path | None
    desktop_access_token: str | None
    media_backend: MediaStorageBackendService | None = None


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


def set_media_backend(media_backend: MediaStorageBackendService):
    _require_ctx().media_backend = media_backend


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


def require_desktop_auth(request: Request):
    if _ctx is None:
        raise RuntimeError("Desktop API router is not configured")
    expected_token = _ctx.desktop_access_token
    if expected_token:
        provided = _extract_bearer_token(request.headers.get("Authorization"))
        if not provided or not hmac.compare_digest(provided, expected_token):
            raise HTTPException(
                status_code=401,
                detail="Unauthorized",
                headers={"WWW-Authenticate": "Bearer"},
            )


def _set_no_cache_headers(response: Response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"


def _desktop_repo_state(branch_name: str) -> dict:
    if not branch_name:
        branch_name = "main"
    try:
        pfm = pamet.project_folder_manager()
    except Exception as e:
        log.warning(f"ProjectFolderManager unavailable for desktop storage state: {e}")
        return {
            "commitGraph": {
                "branches": [{"name": branch_name, "headCommitId": None}],
                "commits": [],
            },
            "commits": [],
        }
    return pfm.get_head_state_as_mock_commit(branch_name=branch_name)


def _require_media_backend() -> MediaStorageBackendService:
    media_backend = _require_ctx().media_backend
    if media_backend is None:
        raise HTTPException(status_code=503, detail="Media backend unavailable")
    return media_backend


@router.post("/commands/{command_name}/")
def run_command(command_name: str):
    commands = _require_ctx().commands
    if command_name in commands:
        commands[command_name]()


@router.get("/version")
def version():
    return envelope(pamet.__version__)


@router.get(
    "/desktop/local-projects",
    dependencies=[Depends(require_desktop_auth)],
)
def get_local_projects(response: Response):
    settings = pamet.get_user_settings()
    local_projects_by_path = desktop_app.get_local_projects()
    local_projects = [
        local_projects_by_path[str(Path(path))]
        for path in settings.recent_projects
    ]
    _set_no_cache_headers(response)
    return local_projects


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
    del project_id
    state = _desktop_repo_state(branch_name=branch)
    _set_no_cache_headers(response)
    return state["commitGraph"]


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
    del project_id
    state = _desktop_repo_state(branch_name=branch)
    commits_by_id = {c["id"]: c for c in state["commits"]}
    commits = [commits_by_id[cid] for cid in ids if cid in commits_by_id]
    _set_no_cache_headers(response)
    return commits


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
async def upload_media(media_id: str, content_hash: str, file: UploadFile = File(...)):
    media_backend = _require_media_backend()
    data = await file.read()
    media_backend.save_bytes(media_id, content_hash, data, file.content_type)
    return {"data": {"ok": True}}


@media_router.get(
    "/item/{media_id}/{content_hash}",
    dependencies=[Depends(require_desktop_auth)],
)
async def get_media_item(media_id: str, content_hash: str):
    media_backend = _require_media_backend()
    path = media_backend.find_item_path(media_id, content_hash)
    if path is None:
        raise HTTPException(status_code=404, detail="Media not found")
    return FileResponse(path)


@media_router.delete(
    "/item/{media_id}/{content_hash}",
    dependencies=[Depends(require_desktop_auth)],
)
async def delete_media(media_id: str, content_hash: str):
    media_backend = _require_media_backend()
    moved = media_backend.move_to_trash(media_id, content_hash)
    if moved:
        return {"data": {"ok": True}}
    return {"data": {"ok": False, "reason": "not_found"}}


@media_router.post(
    "/item/{media_id}/{content_hash}/restore",
    dependencies=[Depends(require_desktop_auth)],
)
async def restore_media(media_id: str, content_hash: str):
    media_backend = _require_media_backend()
    restored = media_backend.restore_from_trash(media_id, content_hash)
    if restored:
        return {"data": {"ok": True}}
    return {"data": {"ok": False, "reason": "not_in_trash"}}


@media_router.post(
    "/trash/clean",
    dependencies=[Depends(require_desktop_auth)],
)
async def clean_trash():
    media_backend = _require_media_backend()
    removed = media_backend.clean_trash()
    return {"data": {"removed": removed}}
