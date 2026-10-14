"""The desktop server's HTTP/WS and shutdown behavior on the Qt event loop."""

import asyncio
import json
import os
import signal
import urllib.request

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from sivkit.platform.qt_widgets.qt_event_loop import uninstall
from sivkit.platform.qt_widgets.qt_main_loop import QtMainLoop
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed

import pamet
from pamet.services.config_file_manager import ConfigFileManager
from pamet.services.rest_api.desktop_server import DesktopServer


def test_desktop_server(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setattr(ConfigFileManager, "_app_config_files", lambda _: [])
    monkeypatch.setattr(DesktopServer, "_pick_port", staticmethod(lambda _: 0))
    app = QApplication.instance() or QApplication([])
    received = []
    previous = signal.signal(signal.SIGTERM, lambda sig, _: received.append(sig))

    async def check():
        for shutdown in ("stop", "signal"):
            server = DesktopServer(config_dir=tmp_path)
            await server.start()
            try:
                port = server.server.servers[0].sockets[0].getsockname()[1]
                with await asyncio.to_thread(
                    urllib.request.urlopen, f"http://127.0.0.1:{port}/version"
                ) as response:
                    assert json.load(response) == {"data": pamet.__version__}
                async with connect(
                    f"ws://127.0.0.1:{port}/config/store/ws",
                    additional_headers={
                        "Cookie": f"pamet_desktop_token={server.desktop_access_token}"
                    },
                ) as ws:
                    assert json.loads(await ws.recv())["type"] == "full_state"
                    if shutdown == "signal":
                        os.kill(os.getpid(), signal.SIGTERM)
                        await asyncio.wait_for(asyncio.shield(server._serve_task), 5)
                        assert received == []  # DesktopServer consumes the signal.
                    else:
                        await asyncio.wait_for(server.stop(), 5)
                    with pytest.raises(ConnectionClosed):
                        await ws.recv()
                    assert not (tmp_path / ".local_server.lock").exists()
            finally:
                await server.stop()

    QtMainLoop(app)
    task = asyncio.get_event_loop().create_task(check())
    task.add_done_callback(lambda _: app.quit())
    guard = QTimer()
    guard.setSingleShot(True)
    guard.timeout.connect(lambda: app.exit(2))
    guard.start(15_000)
    try:
        assert app.exec() == 0
        task.result()
    finally:
        guard.stop()
        signal.signal(signal.SIGTERM, previous)
        uninstall()
