import asyncio
import contextlib
import os
import signal
import threading
import urllib.request

import pytest
import uvicorn
from fastapi import FastAPI, WebSocket
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from sivkit.platform.qt_widgets.qt_event_loop import uninstall
from sivkit.platform.qt_widgets.qt_main_loop import QtMainLoop
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed

from pamet.services.rest_api.desktop_server import DesktopServer
from pamet.services.rest_api.instance_check import get_running_instance_port


@pytest.fixture
def qt_app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    yield app
    uninstall()


def test_uvicorn_on_qt_loop(qt_app):
    """Lifespan, HTTP, WebSocket, shutdown with an open socket, SIGTERM."""
    lifespan_events = []

    @contextlib.asynccontextmanager
    async def lifespan(app):
        lifespan_events.append("startup")
        yield
        lifespan_events.append("shutdown")

    app = FastAPI(lifespan=lifespan)

    @app.get("/")
    async def hello():
        return "hello"

    @app.websocket("/ws")
    async def echo(websocket: WebSocket):
        await websocket.accept()
        async for message in websocket.iter_text():
            await websocket.send_text(message)

    async def start_server():
        config = uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning")
        server = uvicorn.Server(config)
        task = asyncio.ensure_future(server.serve())
        while not server.started:
            assert not task.done(), task.exception()
            await asyncio.sleep(0.01)
        port = server.servers[0].sockets[0].getsockname()[1]
        return server, task, port

    async def check():
        server, serve_task, port = await start_server()
        assert lifespan_events == ["startup"]

        with await asyncio.to_thread(
            urllib.request.urlopen, f"http://127.0.0.1:{port}/"
        ) as response:
            assert response.read() == b'"hello"'

        ws = await connect(f"ws://127.0.0.1:{port}/ws")
        await ws.send("one")
        assert await ws.recv() == "one"

        server.should_exit = True
        await asyncio.wait_for(serve_task, 10)
        assert lifespan_events == ["startup", "shutdown"]
        with pytest.raises(ConnectionClosed):
            await asyncio.wait_for(ws.recv(), 5)

        # uvicorn shuts down, then re-raises the signal to the previous handler
        received = []
        previous = signal.signal(signal.SIGTERM, lambda sig, _: received.append(sig))
        try:
            server, serve_task, port = await start_server()
            threading.Timer(0.2, os.kill, (os.getpid(), signal.SIGTERM)).start()
            await asyncio.wait_for(serve_task, 10)
            assert received == [signal.SIGTERM]
        finally:
            signal.signal(signal.SIGTERM, previous)

    QtMainLoop(qt_app)
    task = asyncio.get_event_loop().create_task(check())
    task.add_done_callback(lambda _: qt_app.quit())
    QTimer.singleShot(30_000, lambda: qt_app.exit(2))  # hang guard
    assert qt_app.exec() == 0
    task.result()


def test_desktop_server_start_stop(tmp_path):
    # Start the server
    server = DesktopServer(config_dir=tmp_path)
    server.start()

    # Check that it's running
    assert get_running_instance_port(tmp_path)

    # Stop the server
    server.stop()

    # Check that it's not running
    assert not get_running_instance_port(tmp_path)
