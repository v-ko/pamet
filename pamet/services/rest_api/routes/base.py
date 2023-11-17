from fastapi import FastAPI
from starlette.responses import FileResponse
from pathlib import Path



class ApiRoutes:

    def __init__(
        self,
        app: FastAPI,
        commands: dict,
        web_app_static_build_path: str | Path = None,
        web_app_debug_server_host: str = None,
    ):
        self.app = app
        self.web_app_static_build_path = web_app_static_build_path
        self.commands = commands

        @self.app.post('/commands/{command_name}/')
        def run_command(command_name: str):
            if command_name in self.commands:
                self.commands[command_name]()

        @self.app.get('/koi/')
        def confirm_is_running():
            return SECRET_REPLY

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
