import threading
from contextlib import asynccontextmanager
from pathlib import Path
from random import randint

import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sivkit import get_logger
from starlette.responses import FileResponse
from uvicorn import Config, Server

from pamet.services.rest_api.desktop_access_token import DESKTOP_ACCESS_TOKEN
from pamet.services.rest_api.instance_check import (
    remove_lock_file,
    write_port_to_lock_file,
)
from pamet.services.rest_api.routes.desktop import desktop_router

log = get_logger(__name__)

DEFAULT_PORT = 11352
LOCALHOST = "http://localhost"

# Maximum time (seconds) to wait for uvicorn to start accepting connections.
_SERVER_STARTUP_TIMEOUT = 10


def port_is_taken(port: int):
    try:
        requests.get(f"{LOCALHOST}:{port}/")  # @IgnoreException
    except requests.ConnectionError:
        return False
    return True


class DesktopServer:

    def __init__(
        self,
        config_dir: Path,
        port: int | None = None,
        web_app_static_build_path: Path | str | None = None,
        frontend_dev_server_url: str | None = None,
    ):
        self.config_dir = Path(config_dir)
        self.desktop_access_token = DESKTOP_ACCESS_TOKEN

        self.web_app_static_build_path = None
        if web_app_static_build_path:
            self.web_app_static_build_path = Path(web_app_static_build_path)

        self.thread = None
        self._port = port or DEFAULT_PORT
        self._ready_event = threading.Event()

        @asynccontextmanager
        async def _lifespan(app: FastAPI):
            self._ready_event.set()
            yield

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
                return FileResponse(index_path)

    @property
    def port(self):
        return self._port

    def start(self):
        log.info("Starting local server")
        # We're assuming a check has been made if another server is running
        # So if there's a lock - we're going to overwrite it
        remove_lock_file(self.config_dir)

        port = self.port
        port_was_taken = False
        while port_is_taken(port):
            port_was_taken = True
            log.warning(f"Port {port} is taken. Trying another one.")
            port = randint(10024, 65535)
        write_port_to_lock_file(self.config_dir, port)

        if port_was_taken:
            log.warning(f"Requested port was taken. Using port {port}.")

        self._port = port
        config = Config(app=self.app, host="127.0.0.1", port=self.port)
        self.server = Server(config=config)

        # Start the server in a thread
        self._ready_event.clear()
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()

        # Block until FastAPI's lifespan startup hook fires (server is ready)
        if not self._ready_event.wait(timeout=_SERVER_STARTUP_TIMEOUT):
            raise RuntimeError(
                f"Server did not become ready within {_SERVER_STARTUP_TIMEOUT}s"
            )

    def stop(self):
        self.server.should_exit = True
        self.server.force_exit = True
        self.thread.join(timeout=3)
        remove_lock_file(self.config_dir)
