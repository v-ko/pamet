from pathlib import Path
from random import randint
import threading
from time import sleep
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
from uvicorn import Config, Server
from pamet.desktop_app.config import pamet_data_folder_path
from fusion import get_logger

log = get_logger(__name__)

SECRET_REPLY = {'result': 'svoi'}
DEFAULT_PORT = 11352


def port_is_taken(port: int):
    try:
        requests.get(f'http://localhost:{port}/')  #@IgnoreException
    except requests.ConnectionError:
        return False
    return True


class LocalServer:

    def __init__(self,
                 commands: dict = None,
                 config_dir: Path | str = None):
        threading.Thread.__init__(self)
        self.commands = commands or {}
        self.config_dir = config_dir or pamet_data_folder_path

        self.thread = None
        self.app = FastAPI()
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=['*'],
            allow_credentials=True,
            allow_methods=['*'],
            allow_headers=['*'],
        )
        self.server = None

    def lock_path(self):
        return self.config_dir / '.local_server.lock'

    def get_port_from_lock_file(self):
        lock_file = self.lock_path()
        if lock_file.exists():
            port = lock_file.read_text()
            return int(port)
        else:
            return None

    def write_port_to_lock_file(self, port: int):
        lock_file = self.lock_path()
        lock_file.write_text(str(port))

    def another_instance_is_running(self):
        port = self.get_port_from_lock_file()

        if port is None:
            return False

        # Check with a request
        try:
            reply = requests.get(f'http://localhost:{port}/koi')  #@IgnoreException
            if reply.json() == SECRET_REPLY:
                return True
        except requests.ConnectionError:
            return False
        return True

    def start(self, port: int = None):
        # We're assuming a check has been made if another server is running
        # So if there's a lock - we're going to overwrite it
        self.lock_path().unlink(missing_ok=True)

        port = port or DEFAULT_PORT
        while port_is_taken(port):
            log.warning(f'Port {port} is taken. Trying another one.')
            port = randint(10024, 65535)
        self.write_port_to_lock_file(port)

        # Start the server in a thread
        self.thread = threading.Thread(target=self._run, args=(port,))
        self.thread.start()

    def _run(self, port: int):

        @self.app.post('/commands/{command_name}/')
        def run_command(command_name: str):
            if command_name in self.commands:
                self.commands[command_name]()

        @self.app.get('/koi/')
        def confirm_is_running():
            return SECRET_REPLY

        config = Config(app=self.app, host='127.0.0.1', port=port)
        self.server = Server(config=config)
        self.server.run()

    def stop(self):
        self.server.should_exit = True
        # self.server.should_exit.set()
        self.thread.join()

        # Remove the lock file
        lock_file = self.lock_path()
        lock_file.unlink()

    @staticmethod
    def send_command(port: int, command_name: str):
        requests.post(f'http://localhost:{port}/commands/{command_name}/')


if __name__ == '__main__':
    server = LocalServer()
    server.start()
    sleep(10)
    server.stop()
