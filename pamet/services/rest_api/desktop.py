from pathlib import Path
from random import randint
import threading
from time import sleep
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse

from fastapi.middleware.cors import CORSMiddleware
import requests
from uvicorn import Config, Server
from fusion.libs.entity import dump_to_dict
import pamet
from pamet.desktop_app.config import pamet_data_folder_path
from fusion import get_logger
from pamet.services.rest_api.util import envelope

log = get_logger(__name__)

SECRET_REPLY = {'result': 'svoi'}
DEFAULT_PORT = 11352
LOCALHOST = 'http://localhost'


def port_is_taken(port: int):
    try:
        requests.get(f'{LOCALHOST}:{port}/')  #@IgnoreException
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
        self.config_dir = config_dir or pamet_data_folder_path

        self.web_app_static_build_path = None
        if web_app_static_build_path:
            self.web_app_static_build_path = Path(web_app_static_build_path)
        self.web_app_debug_server_host = web_app_debug_server_host

        self.thread = None
        self._port = port or DEFAULT_PORT
        print(f'In the constructor the port is {self._port}')

        self.app = FastAPI()
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=['*'],
            allow_credentials=True,
            allow_methods=['*'],
            allow_headers=['*'],
        )

        # Define routes
        @self.app.post('/commands/{command_name}/')
        def run_command(command_name: str):
            if command_name in self.commands:
                self.commands[command_name]()

        @self.app.get('/version')
        def version():
            return envelope(pamet.__version__)

        # Serve the React app static dir
        if web_app_static_build_path and web_app_debug_server_host:
            raise Exception(
                'Cannot serve static build path and debug server host at '
                'the same time')

        if self.web_app_static_build_path:

            @self.app.get('/')
            def serve_index():
                index_path = self.web_app_static_build_path / 'index.html'
                print(f'Serving index: {index_path}')
                return FileResponse(index_path)

            @self.app.get('/static/{path:path}')
            def serve_static(path: str):
                static_path = self.web_app_static_build_path / 'static' / path
                print(f'Serving static: {static_path}')
                return FileResponse(static_path)

        @self.app.get('/pages')
        def get_pages(responce: Response):
            pages = [dump_to_dict(page) for page in pamet.pages()]

            # set nocache headers
            responce.headers[
                'Cache-Control'] = 'no-cache, no-store, must-revalidate'  # noqa: E501
            responce.headers['Pragma'] = 'no-cache'
            responce.headers['Expires'] = '0'

            return envelope(pages)

        @self.app.get('/p/{page_id}/children')
        def get_children(page_id: str, responce: Response):
            page = pamet.page(page_id)
            if not page:
                raise HTTPException(status_code=404, detail='Page not found')

            note_dicts = []
            for note in pamet.notes(page_id):
                note_dict = note.asdict()
                note_dict['type'] = type(note).__name__
                note_dicts.append(note_dict)

            arrow_dicts = []
            for arrow in pamet.arrows(page_id):
                arrow_dict = arrow.asdict()
                arrow_dict['type'] = type(arrow).__name__
                arrow_dicts.append(arrow_dict)

            # set nocache headers
            responce.headers[
                'Cache-Control'] = 'no-cache, no-store, must-revalidate'  # noqa: E501
            responce.headers['Pragma'] = 'no-cache'
            responce.headers['Expires'] = '0'

            return envelope({
                'notes': note_dicts,
                'arrows': arrow_dicts,
            })

        @self.app.get('/desktop/fs/{path:path}')
        def get_file(path: str):
            file_path = Path('/') / path
            if not file_path.exists():
                raise HTTPException(status_code=404, detail='File not found')
            return FileResponse(file_path)

        @self.app.get('/p/{page_id}/media/{path:path}')
        def get_media(page_id: str, path: str):
            file_path = self.media_store_path / page_id / path

            if not file_path.exists():
                raise HTTPException(status_code=404, detail='File not found')
            return FileResponse(file_path)

    @property
    def port(self):
        return self._port

    # File lock mechanism
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

        # Check with a request (it's just a sanity check)
        try:
            reply = requests.get(
                f'{LOCALHOST}:{port}/version')  #@IgnoreException
            if not reply.ok:
                return False
            if 'data' in reply.json():
                return True
        except requests.ConnectionError:
            return False
        return True

    def start(self):
        log.info('Starting local server')
        # We're assuming a check has been made if another server is running
        # So if there's a lock - we're going to overwrite it
        self.lock_path().unlink(missing_ok=True)

        port = self.port
        port_was_taken = False
        while port_is_taken(port):
            port_was_taken = True
            log.warning(f'Port {port} is taken. Trying another one.')
            port = randint(10024, 65535)
        self.write_port_to_lock_file(port)

        if port_was_taken:
            log.warning(f'Requested port was taken. Using port {port}.')

        self._port = port
        config = Config(app=self.app, host='127.0.0.1', port=self.port)
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
        requests.post(f'{LOCALHOST}:{port}/commands/{command_name}/')


if __name__ == '__main__':
    server = DesktopServer()
    server.start()
    sleep(10)
    server.stop()
