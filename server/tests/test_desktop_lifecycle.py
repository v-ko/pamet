"""Project loading, closing, and shutdown integration."""

import asyncio
import threading
from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication

import pamet
from pamet.model.page import Page
from pamet.services import desktop_storage_service as storage
from pamet.services.project_sync.project_folder_manager import ProjectSnapshot
from pamet.services.rest_api.routes import desktop as routes


@pytest.fixture
def dss(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(storage.ConfigFileManager, "_app_config_files", lambda _: [])
    monkeypatch.setattr(storage, "scan_project", lambda *_: ProjectSnapshot())
    service = storage.DesktopStorageService()
    monkeypatch.setattr(pamet, "desktop_storage_service", lambda: service)
    yield service
    assert app is not None


class WorkerGate:
    def __init__(self):
        self.loop = asyncio.get_running_loop()
        self.started = asyncio.Event()
        self.release = threading.Event()

    def wait(self):
        self.loop.call_soon_threadsafe(self.started.set)
        assert self.release.wait(5), "worker gate timed out"


def run(coro):
    async def bounded():
        await asyncio.wait_for(coro, 10)

    asyncio.run(bounded())


def test_project_loading(dss, tmp_path, monkeypatch):
    async def check():
        gate = WorkerGate()
        scans = []

        def scan(*args):
            scans.append(args)
            gate.wait()
            return ProjectSnapshot()

        # Concurrent callers share initialization even if one disconnects.
        monkeypatch.setattr(storage, "scan_project", scan)
        first = asyncio.create_task(dss.load_project("p", tmp_path))
        await gate.started.wait()
        second = asyncio.create_task(dss.load_project("p", tmp_path))
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first
        gate.release.set()
        await second
        assert len(scans) == 1
        assert dss.project_folder_manager("p").repo_root == tmp_path
        await dss.unload_project("p")

        # A failed initialization must leave the project usable after repair.
        properties = tmp_path / ".pamet" / "properties.json"
        saved = properties.read_text()
        properties.write_text("invalid json")
        with pytest.raises(ValueError):
            await dss.load_project("p", tmp_path)
        properties.write_text(saved)
        await dss.load_project("p", tmp_path)
        assert dss.project_folder_manager("p").repo_root == tmp_path
        await dss.close()

    run(check())


@pytest.mark.parametrize("shutdown", [False, True], ids=["unload", "shutdown"])
def test_closing_during_load(dss, tmp_path, monkeypatch, shutdown):
    async def check():
        gate = WorkerGate()

        def scan(*_):
            gate.wait()
            return ProjectSnapshot()

        monkeypatch.setattr(storage, "scan_project", scan)
        loading = asyncio.create_task(dss.load_project("p", tmp_path))
        await gate.started.wait()
        closing = asyncio.create_task(
            dss.close() if shutdown else dss.unload_project("p")
        )
        await asyncio.sleep(0)
        assert not closing.done()
        with pytest.raises(storage.StorageClosingError):
            await dss.load_project("p", tmp_path)
        gate.release.set()
        with pytest.raises(storage.StorageClosingError):
            await loading
        await closing
        with pytest.raises(
            (storage.StorageClosingError, storage.ProjectNotLoadedError)
        ):
            dss.project_folder_manager("p")
        await dss.close()

    run(check())


@pytest.mark.parametrize(
    "backup_fails", [False, True], ids=["backup", "backup-failure"]
)
def test_project_teardown(dss, tmp_path, monkeypatch, backup_fails):
    page = Page(path="page.canvas.html")
    monkeypatch.setattr(
        storage, "scan_project", lambda *_: ProjectSnapshot(entities=[page])
    )

    async def check():
        await dss.load_project("p", tmp_path)
        pfm = dss.project_folder_manager("p")
        backup = pfm.backup_service
        # Stop periodic work so only teardown can flush this pending page.
        await backup.close()
        backup.mark_pages_changed({page.id})
        assert not backup.recent_backups_for_page("page")
        if backup_fails:

            async def failed_flush():
                raise OSError("backup denied")

            monkeypatch.setattr(backup, "close", failed_flush)

        gate = WorkerGate()

        def integrity(fix, post):
            gate.wait()
            return {"total": 0, "mismatches": 0, "log_path": str(tmp_path / "log")}

        history = dss.change_history_service("p")
        monkeypatch.setattr(history, "_run_integrity", integrity)
        monkeypatch.setattr(
            routes, "QDesktopServices", SimpleNamespace(openUrl=lambda _: None)
        )
        changes = await routes.project_changes_stream("p")
        progress = routes._start_integrity_run("p", False)
        streams = [
            asyncio.create_task(anext(response.body_iterator))
            for response in (changes, progress)
        ]
        await gate.started.wait()

        unloading = asyncio.create_task(dss.unload_project("p"))
        for stream in streams:
            with pytest.raises(StopAsyncIteration):
                await stream
        # Streams end promptly; the runtime stays alive until history finishes.
        assert not unloading.done()
        assert pfm.store.find_one(id=page.id) is not None
        gate.release.set()
        await unloading
        assert list(pfm.store.find()) == []
        if not backup_fails:
            assert len(backup.recent_backups_for_page("page")) == 1
        await dss.close()

    run(check())
