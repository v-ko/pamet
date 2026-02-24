import threading
from pathlib import Path
from random import randint
from time import sleep

import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pamet.services.media_backend import MediaStorageBackendService
from pamet.services.rest_api.auth import DESKTOP_ACCESS_TOKEN
from pamet.services.rest_api.routes.desktop import (
    configure_router,
    get_media_router,
    get_router,
    set_media_backend,
)
from uvicorn import Config, Server

import pamet
from fusion import get_logger

log = get_logger(__name__)

SECRET_REPLY = {"result": "svoi"}
DEFAULT_PORT = 11352
LOCALHOST = "http://localhost"


def port_is_taken(port: int):
    try:
        requests.get(f"{LOCALHOST}:{port}/")  # @IgnoreException
    except requests.ConnectionError:
        return False
    return True


class DesktopServer:

    def __init__(
        self,
        media_store_path: Path | str,
        port: int = None,
        commands: dict = None,
        config_dir: Path | str = None,
        web_app_static_build_path: Path | str = None,
        web_app_debug_server_host: str = None,
    ):
        threading.Thread.__init__(self)
        self.media_store_path = Path(media_store_path)
        self.commands = commands or {}
        if config_dir is None:
            config_dir = pamet.desktop_app.desktop_config_dir()
        self.config_dir = Path(config_dir)
        self.desktop_access_token = DESKTOP_ACCESS_TOKEN

        self.web_app_static_build_path = None
        if web_app_static_build_path:
            self.web_app_static_build_path = Path(web_app_static_build_path)
        self.web_app_debug_server_host = web_app_debug_server_host
        self._media_routes_registered = False

        self.thread = None
        self._port = port or DEFAULT_PORT

        self.app = FastAPI()
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

        configure_router(
            commands=self.commands,
            media_store_path=self.media_store_path,
            web_app_static_build_path=self.web_app_static_build_path,
            desktop_access_token=self.desktop_access_token,
        )
        self.app.include_router(get_router())
        self.app.include_router(get_media_router())

        # Media routes are registered once the backend service is available.
        try:
            media_backend = pamet.media_backend_service()
            self.register_media_routes(media_backend)
        except Exception:
            # Expected during startup before desktop main sets the service.
            pass

    def register_media_routes(self, media_backend: MediaStorageBackendService):
        if self._media_routes_registered:
            return
        set_media_backend(media_backend)
        self._media_routes_registered = True
        log.info("MediaStorageBackendService routes registered")

    @property
    def port(self):
        return self._port

    # File lock mechanism
    def lock_path(self):
        return self.config_dir / ".local_server.lock"

    def get_port_from_lock_file(self):
        lock_file = self.lock_path()
        if lock_file.exists():
            port = lock_file.read_text()
            return int(port)
        else:
            return None

    def write_port_to_lock_file(self, port: int):
        lock_file = self.lock_path()
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        lock_file.write_text(str(port))

    def another_instance_is_running(self):
        port = self.get_port_from_lock_file()

        if port is None:
            return False

        # Check with a request (it's just a sanity check)
        try:
            reply = requests.get(f"{LOCALHOST}:{port}/version")  # @IgnoreException
            if not reply.ok:
                return False
            if "data" in reply.json():
                return True
        except requests.ConnectionError:
            return False
        return True

    def start(self):
        log.info("Starting local server")
        # We're assuming a check has been made if another server is running
        # So if there's a lock - we're going to overwrite it
        self.lock_path().unlink(missing_ok=True)

        port = self.port
        port_was_taken = False
        while port_is_taken(port):
            port_was_taken = True
            log.warning(f"Port {port} is taken. Trying another one.")
            port = randint(10024, 65535)
        self.write_port_to_lock_file(port)

        if port_was_taken:
            log.warning(f"Requested port was taken. Using port {port}.")

        self._port = port
        config = Config(app=self.app, host="127.0.0.1", port=self.port)
        self.server = Server(config=config)

        # Start the server in a thread
        self.thread = threading.Thread(target=self.server.run)
        self.thread.start()

    def stop(self):
        self.server.should_exit = True
        self.thread.join()

        # Remove the lock file
        lock_file = self.lock_path()
        lock_file.unlink()

    @staticmethod
    def send_command(port: int, command_name: str):
        requests.post(f"{LOCALHOST}:{port}/commands/{command_name}/")
