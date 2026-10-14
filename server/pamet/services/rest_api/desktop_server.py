import asyncio
import contextlib
import logging
import signal
from collections.abc import Callable
from contextlib import asynccontextmanager
from pathlib import Path
from random import randint

import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
from uvicorn import Config, Server
from uvicorn.server import HANDLED_SIGNALS

import pamet
from pamet.services.desktop_storage_service import DesktopStorageService
from pamet.services.rest_api.desktop_access_token import DESKTOP_ACCESS_TOKEN
from pamet.services.rest_api.instance_check import (
    remove_lock_file,
    write_port_to_lock_file,
)
from pamet.services.rest_api.routes.desktop import desktop_router

log = logging.getLogger(__name__)

DEFAULT_PORT = 11352
LOCALHOST = "http://localhost"


def port_is_taken(port: int):
    try:
        requests.get(f"{LOCALHOST}:{port}/")  # @IgnoreException
    except requests.ConnectionError:
        return False
    return True


class _Server(Server):
    """Signals call ``on_signal`` instead of being re-raised after ``serve()``."""

    def __init__(self, config: Config, on_signal: Callable[[], None]):
        super().__init__(config)
        self._on_signal = on_signal

    @contextlib.contextmanager
    def capture_signals(self):
        loop = asyncio.get_running_loop()

        def handle(sig, frame):
            loop.call_soon_threadsafe(self._on_signal)

        previous = {sig: signal.signal(sig, handle) for sig in HANDLED_SIGNALS}
        try:
            yield
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)


class DesktopServer:
    """Uvicorn as a task on the running (Qt) loop. Its lifespan owns the DSS."""

    def __init__(
        self,
        config_dir: Path,
        port: int | None = None,
        web_app_static_build_path: Path | str | None = None,
        frontend_dev_server_url: str | None = None,
        on_signal: Callable[[], None] | None = None,
    ):
        self.config_dir = Path(config_dir)
        self.desktop_access_token = DESKTOP_ACCESS_TOKEN

        self.web_app_static_build_path = None
        if web_app_static_build_path:
            self.web_app_static_build_path = Path(web_app_static_build_path)

        self._port = self._pick_port(port or DEFAULT_PORT)
        self._on_signal = on_signal or self._exit
        self.server: _Server | None = None
        self._serve_task: asyncio.Task | None = None
        self._storage_service: DesktopStorageService | None = None

        @asynccontextmanager
        async def _lifespan(app: FastAPI):
            dss = DesktopStorageService()
            self._storage_service = dss
            pamet.set_desktop_storage_service(dss)
            try:
                yield
            finally:
                await dss.close()

        self.app = FastAPI(lifespan=_lifespan)
        if frontend_dev_server_url:
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=[frontend_dev_server_url.rstrip("/")],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

        self.app.state.web_app_static_build_path = self.web_app_static_build_path
        self.app.state.desktop_access_token = self.desktop_access_token

        # API routes are registered first so they win over the SPA static
        # mount below (which acts as a catch-all serving index.html).
        self.app.include_router(desktop_router)

        if self.web_app_static_build_path:
            build_path = self.web_app_static_build_path
            index_path = build_path / "index.html"
            if not index_path.exists():
                raise FileNotFoundError(
                    f"web_app_static_build_path {build_path} has no "
                    "index.html — did you run `npm run build:desktop`?"
                )

            # Real assets (hashed JS/CSS/maps) — return 404 on miss so the
            # browser surfaces a clear error instead of HTML-as-JS garbage.
            self.app.mount(
                "/assets",
                StaticFiles(directory=build_path / "assets"),
                name="web_app_assets",
            )

            # Everything else: serve the file at the build root if it
            # exists (favicon.ico, logo256.png, manifest.json, …),
            # otherwise fall back to index.html so the SPA router takes
            # over. The SPA itself reports 404 for unknown routes.
            @self.app.get("/{spa_path:path}", include_in_schema=False)
            async def spa_fallback(spa_path: str):
                candidate = (build_path / spa_path).resolve()
                if spa_path and build_path in candidate.parents and candidate.is_file():
                    return FileResponse(candidate)
                # index.html references content-hashed assets; never cache the
                # document itself or a stale copy pins the old asset graph.
                return FileResponse(index_path, headers={"Cache-Control": "no-store"})

    @property
    def port(self):
        return self._port

    @staticmethod
    def _pick_port(port: int) -> int:
        requested = port
        while port_is_taken(port):
            log.warning(f"Port {port} is taken. Trying another one.")
            port = randint(10024, 65535)
        if port != requested:
            log.warning(f"Requested port was taken. Using port {port}.")
        return port

    async def start(self) -> None:
        """Start serving and return once the socket accepts connections."""
        log.info("Starting local server")
        config = Config(
            app=self.app,
            host="127.0.0.1",
            port=self._port,
            timeout_graceful_shutdown=2,
        )
        self.server = _Server(config, self._on_signal)
        self._serve_task = asyncio.ensure_future(self._serve(self.server))
        # Lifespan startup runs before the socket is bound, so wait for started
        while not self.server.started:
            if self._serve_task.done():
                self._serve_task.result()
                raise RuntimeError("Server exited during startup")
            await asyncio.sleep(0.01)

        # Another running instance was ruled out before, so a lock is stale
        write_port_to_lock_file(self.config_dir, self._port)
        self._serve_task.add_done_callback(lambda _: remove_lock_file(self.config_dir))

    async def stop(self) -> None:
        """Graceful shutdown, including the lifespan shutdown. Idempotent."""
        assert self.server is not None and self._serve_task is not None
        self._exit()
        await asyncio.shield(self._serve_task)

    @staticmethod
    async def _serve(server: _Server) -> None:
        try:
            await server.serve()
        except SystemExit as exc:
            # uvicorn calls sys.exit() when it can't bind
            raise RuntimeError(f"Server exited with code {exc.code}") from exc

    def _exit(self) -> None:
        if self._storage_service is not None:
            self._storage_service.begin_closing()
        if self.server is not None:
            self.server.should_exit = True
