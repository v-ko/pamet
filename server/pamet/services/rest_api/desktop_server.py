import threading
from contextlib import asynccontextmanager
from pathlib import Path
from random import randint

import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fusion import get_logger
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
        port: int = None,
        web_app_static_build_path: Path | str = None,
        web_app_debug_server_host: str = None,
    ):
        self.config_dir = Path(config_dir)
        self.desktop_access_token = DESKTOP_ACCESS_TOKEN

        self.web_app_static_build_path = None
        if web_app_static_build_path:
            self.web_app_static_build_path = Path(web_app_static_build_path)
        self.web_app_debug_server_host = web_app_debug_server_host

        self.thread = None
        self._port = port or DEFAULT_PORT
        self._ready_event = threading.Event()

        @asynccontextmanager
        async def _lifespan(app: FastAPI):
            self._ready_event.set()
            yield

        self.app = FastAPI(lifespan=_lifespan)
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Serve static build OR external dev server, but not both.
        if web_app_static_build_path and web_app_debug_server_host:
            raise Exception(
                "Cannot serve static build path and debug server host at "
                "the same time"
            )

        self.app.state.web_app_static_build_path = self.web_app_static_build_path
        self.app.state.desktop_access_token = self.desktop_access_token

        self.app.include_router(desktop_router)

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
        self.thread = threading.Thread(target=self.server.run)
        self.thread.start()

        # Block until FastAPI's lifespan startup hook fires (server is ready)
        if not self._ready_event.wait(timeout=_SERVER_STARTUP_TIMEOUT):
            raise RuntimeError(
                f"Server did not become ready within {_SERVER_STARTUP_TIMEOUT}s"
            )

    def stop(self):
        self.server.should_exit = True
        self.thread.join()
        remove_lock_file(self.config_dir)
