"""The desktop server's HTTP/WS and shutdown behavior on the Qt event loop."""

import asyncio
import json
import os
import signal
import threading
import urllib.error
import urllib.request

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from sivkit.libs import command as commands
from sivkit.libs.command import Command
from sivkit.libs.model import dump_to_dict
from sivkit.platform.qt_widgets.qt_event_loop import uninstall
from sivkit.platform.qt_widgets.qt_main_loop import QtMainLoop
from sivkit.storage.change import Change
from sivkit.storage.delta import Delta
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed

import pamet
from pamet.model.card_note import CardNote
from pamet.model.page import Page
from pamet.services.config_file_manager import ConfigFileManager
from pamet.services.rest_api.desktop_server import DesktopServer


@pytest.fixture
def run_on_qt(monkeypatch):
    """Run a coroutine on the Qt event loop, as the desktop app does."""
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setattr(ConfigFileManager, "_app_config_files", lambda _: [])
    monkeypatch.setattr(DesktopServer, "_pick_port", staticmethod(lambda _: 0))
    app = QApplication.instance() or QApplication([])

    def run(check):
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
            uninstall()

    return run


def server_port(server):
    return server.server.servers[0].sockets[0].getsockname()[1]


def auth_cookie(server):
    return {"Cookie": f"pamet_desktop_token={server.desktop_access_token}"}


def test_desktop_server(tmp_path, run_on_qt):
    """The server answers HTTP and WS, and both stop() and SIGTERM shut it down
    cleanly: clients are disconnected and the lock file is removed."""
    received = []
    previous = signal.signal(signal.SIGTERM, lambda sig, _: received.append(sig))

    async def check():
        for shutdown in ("stop", "signal"):
            server = DesktopServer(config_dir=tmp_path)
            await server.start()
            try:
                port = server_port(server)
                with await asyncio.to_thread(
                    urllib.request.urlopen, f"http://127.0.0.1:{port}/version"
                ) as response:
                    assert json.load(response) == {"data": pamet.__version__}
                async with connect(
                    f"ws://127.0.0.1:{port}/config/store/ws",
                    additional_headers=auth_cookie(server),
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

    try:
        run_on_qt(check)
    finally:
        signal.signal(signal.SIGTERM, previous)


def test_project_round_trip(tmp_path, run_on_qt, monkeypatch):
    """A web client's session with one project: open it, edit its config, save
    changes, run a GUI command, then close it."""
    project = tmp_path / "project"
    project.mkdir()
    page = Page()
    canvas = project / "page.canvas.html"
    canvas.write_text(json.dumps({**dump_to_dict(page), "notes": [], "arrows": []}))
    calls = []

    def record_call(**context):
        calls.append((context, threading.current_thread() is threading.main_thread()))

    monkeypatch.setitem(
        commands._commands, "test-command", Command(record_call, "Test", "test-command")
    )

    async def check():
        server = DesktopServer(config_dir=tmp_path / "config")
        await server.start()
        port = server_port(server)

        def call(method, path, body=None):
            request = urllib.request.Request(
                f"http://127.0.0.1:{port}{path}",
                method=method,
                headers={**auth_cookie(server), "Content-Type": "application/json"},
                data=None if body is None else json.dumps(body).encode(),
            )
            try:
                with urllib.request.urlopen(request, timeout=5) as response:
                    return response.status, json.load(response)
            except urllib.error.HTTPError as error:
                return error.code, None

        async def http(method, path, body=None):
            return await asyncio.to_thread(call, method, path, body)

        try:
            async with connect(
                f"ws://127.0.0.1:{port}/config/store/ws",
                additional_headers=auth_cookie(server),
            ) as ws:
                server_seq = json.loads(await ws.recv())["seq"]
                pushed = {}
                acks = asyncio.Queue()
                received_push, acking = asyncio.Event(), asyncio.Event()

                # Plays the web app's config sync: collects pushes and acks them
                # once the test sets `acking`.
                async def client():
                    nonlocal server_seq
                    async for raw in ws:
                        msg = json.loads(raw)
                        if msg["type"] == "ack":
                            acks.put_nowait(msg["seq"])
                        elif msg["type"] == "delta":
                            server_seq = msg["seq"]
                            for entity_id, _, forward in msg["delta"].values():
                                pushed.setdefault(entity_id, {}).update(forward)
                            received_push.set()
                            await acking.wait()
                            await ws.send(
                                json.dumps({"type": "ack", "seq": server_seq})
                            )

                reader = asyncio.create_task(client())

                # Opening returns after the client acknowledges the project's config.
                bridge = "/desktop/projects/p/bridge"
                ok = (200, {"ok": True})
                opening = asyncio.create_task(
                    http("PUT", bridge, {"uri": project.as_uri()})
                )
                await asyncio.wait_for(received_push.wait(), 5)
                await asyncio.sleep(0.1)
                assert not opening.done()
                acking.set()
                assert await opening == ok
                props_id = "project-props-p"
                title = pushed[props_id]["title"]

                # The ACK accepts the edit in memory; disk persistence is queued.
                change = [props_id, {"title": title}, {"title": "Renamed"}]
                await ws.send(
                    json.dumps(
                        {
                            "type": "delta",
                            "seq": 1,
                            "base_seq": server_seq,
                            "delta": {props_id: change},
                        }
                    )
                )
                assert await asyncio.wait_for(acks.get(), 5) == 1
                await server._storage_service._config_file_manager.flush(props_id)
                properties = (project / ".pamet" / "properties.json").read_text()
                assert json.loads(properties)["title"] == "Renamed"

                # Project changes reach the store and the page file.
                note = CardNote(parent_id=page.id)
                delta = Delta.from_changes([Change.create(note)]).asdict()
                changes = "/desktop/projects/p/changes"
                assert await http("POST", changes, {"delta": delta}) == ok
                _, body = await http("GET", "/desktop/projects/p/entities")
                assert {e["id"] for e in body["entities"]} == {page.id, note.id}
                assert note.id in canvas.read_text()

                # GUI commands run on the main thread.
                command_path = "/desktop/gui/commands/test-command/"
                assert await http("POST", command_path, {"value": 1}) == ok
                assert calls == [({"value": 1}, True)]

                assert await http("DELETE", bridge) == ok
                reader.cancel()
        finally:
            await server.stop()

    run_on_qt(check)
