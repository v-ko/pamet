"""Project loading, closing, and shutdown integration."""

import asyncio
import json
import os
import threading
from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, UploadFile
from PySide6.QtWidgets import QApplication
from sivkit.libs.model import dump_to_dict, load_from_dict
from sivkit.storage.change import Change
from sivkit.storage.delta import Delta
from sivkit.storage.fs import changes as file_changes

import pamet
from pamet.model.card_note import CardNote
from pamet.model.config import ProjectProperties, UserSettings
from pamet.model.page import Page
from pamet.services import desktop_storage_service as storage
from pamet.services.project_sync.project_folder_manager import (
    ProjectSnapshot,
    scan_project,
)
from pamet.services.rest_api.routes import desktop as routes
from pamet.storage import file_storage_adapter as media
from pamet.storage.canvas_writes import SaveRejected
from pamet.storage.service_utils import read_canvas_file


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


def write_canvas(path, page, notes, mtime=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({**dump_to_dict(page), "notes": notes, "arrows": []}))
    if mtime is not None:
        os.utime(path, (mtime, mtime))


def test_content_boundaries(dss, tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "scan_project", scan_project)
    visible = Page()
    write_canvas(tmp_path / ".private" / "note.canvas.html", visible, [])
    for folder in (".pamet", ".PAMET", ".git"):
        write_canvas(tmp_path / folder / "hidden.canvas.html", Page(), [])

    async def check():
        await dss.load_project("p", tmp_path)
        pfm = dss.project_folder_manager("p")
        assert {e.id for e in pfm.store.find()} == {visible.id}
        # Ordinary dot-folder attachments are not discovery permissions.
        path = ".git/image.png"
        result = await routes.upload_file("u", "p", path, UploadFile(BytesIO(b"image")))
        assert result["hash"] == pfm.file_storage.get_hash(path)
        assert (await routes.get_file("u", "p", path)).path == tmp_path / path
        await routes.delete_file("u", "p", path)
        assert not (tmp_path / path).exists()

        for path in (".pamet/properties.json", ".private/note.canvas.html"):
            target = tmp_path / path
            before = target.read_bytes() if target.exists() else None
            with pytest.raises(HTTPException) as get_error:
                await routes.get_file("u", "p", path)
            assert get_error.value.status_code == 404
            with pytest.raises(HTTPException) as upload_error:
                await routes.upload_file("u", "p", path, UploadFile(BytesIO(b"bad")))
            assert upload_error.value.status_code == 400
            with pytest.raises(HTTPException) as delete_error:
                await routes.delete_file("u", "p", path)
            assert delete_error.value.status_code == 400
            assert (target.read_bytes() if target.exists() else None) == before

        page = Page(path=".PAMET/new.canvas.html")
        with pytest.raises(SaveRejected):
            await dss.save_changes(
                "p", Delta.from_changes([Change.create(page)]).asdict()
            )
        assert pfm.store.find_one(id=page.id) is None
        props = dss.config_store.find_one(id=ProjectProperties.id_for_project("p"))
        props.files_exclude = {".private": True}
        props.canvas_palette = {"dark": {"background": "#123456"}}
        dss.config_store.update_one(props)
        # The explicit map replaces the default, and survives entity persistence.
        await dss.unload_project("p")
        await dss.load_project("p", tmp_path)
        props = dss.config_store.find_one(id=ProjectProperties.id_for_project("p"))
        assert props.files_exclude == {".private": True}
        assert props.canvas_palette == {"dark": {"background": "#123456"}}
        assert (
            load_from_dict(
                dump_to_dict(ProjectProperties(files_exclude={}))
            ).files_exclude
            == {}
        )
        pages = list(dss.project_folder_manager("p").store.find(type=Page))
        assert [page.path for page in pages] == [".git/hidden.canvas.html"]
        user = UserSettings(id="user-settings", themePreference="dark")
        assert load_from_dict(dump_to_dict(user)).themePreference == "dark"
        await dss.close()

    run(check())


def test_media_drains_after_cancelled_request(dss, tmp_path, monkeypatch):
    async def check():
        await dss.load_project("p", tmp_path)
        gate = WorkerGate()
        write_new = media._write_new

        def blocked_write(*args):
            gate.wait()
            return write_new(*args)

        monkeypatch.setattr(media, "_write_new", blocked_write)
        upload = asyncio.create_task(dss.add_file("p", "images/a.png", b"image"))
        await gate.started.wait()
        upload.cancel()
        with pytest.raises(asyncio.CancelledError):
            await upload
        deletion = asyncio.create_task(dss.remove_file("p", "images/a.png"))
        await asyncio.sleep(0)
        assert not deletion.done()
        closing = asyncio.create_task(dss.unload_project("p"))
        await asyncio.sleep(0)
        assert not closing.done()
        with pytest.raises(storage.StorageClosingError):
            await dss.add_file("p", "late.png", b"late")
        gate.release.set()
        assert await deletion
        await closing
        assert not (tmp_path / "images/a.png").exists()
        await dss.close()

    run(check())


def test_save_validation_and_conflicts(dss, tmp_path):
    async def save(*changes):
        return await routes.apply_changes(
            "p", {"delta": Delta.from_changes(changes).asdict()}
        )

    async def check():
        await dss.load_project("p", tmp_path)
        store = dss.project_folder_manager("p").store
        page = Page(path="page.canvas.html")
        await save(Change.create(page))
        original = (tmp_path / page.path).read_bytes()
        invalid = [
            [Page(path=f"{name}.canvas.html")]
            for name in ("a:b", "CON", "cafe\u0301", "../escape", "/absolute")
        ]
        invalid.append([Page(path="Notes.canvas.html"), Page(path="notes.canvas.html")])
        for pages in invalid:
            edited = page.copy()
            edited.modified = "rejected"
            with pytest.raises(HTTPException) as error:
                await save(
                    Change.update(page, edited), *(Change.create(p) for p in pages)
                )
            assert error.value.status_code == 400
            assert store.find_one(id=page.id).modified == page.modified
            assert all(store.find_one(id=p.id) is None for p in pages)
            assert (tmp_path / page.path).read_bytes() == original

        for filename, status in (
            ("foreign.canvas.html", 409),
            ("FOREIGN.canvas.html", 400),
        ):
            foreign = tmp_path / filename
            foreign.write_bytes(b"not a Pamet page")
            refused = Page(path="foreign.canvas.html")
            current = store.find_one(id=page.id)
            edited = current.copy()
            edited.modified = filename
            with pytest.raises(HTTPException) as error:
                await save(Change.create(refused), Change.update(current, edited))
            assert error.value.status_code == status
            assert foreign.read_bytes() == b"not a Pamet page"
            assert store.find_one(id=refused.id) is not None
            assert (
                read_canvas_file(tmp_path / page.path, tmp_path)[page.id].modified
                == filename
            )
            # Another edit must still refuse the foreign target, not overwrite it.
            retry = refused.copy()
            retry.modified = "retry"
            with pytest.raises(HTTPException):
                await save(Change.update(refused, retry))
            assert foreign.read_bytes() == b"not a Pamet page"
            await save(Change.delete(store.find_one(id=refused.id)))
            assert foreign.exists()
            foreign.unlink()

        with pytest.raises(HTTPException) as error:
            await routes.upload_file("u", "p", "a:b.png", UploadFile(BytesIO(b"image")))
        assert error.value.status_code == 400
        assert not (tmp_path / "a:b.png").exists()
        await dss.close()

    run(check())


def test_save_moves_swaps_and_partial_failures(dss, tmp_path, monkeypatch):
    async def save(*changes):
        return await routes.apply_changes(
            "p", {"delta": Delta.from_changes(changes).asdict()}
        )

    async def check():
        await dss.load_project("p", tmp_path)
        store = dss.project_folder_manager("p").store
        first, second = Page(path="first.canvas.html"), Page(path="second.canvas.html")
        await save(Change.create(first), Change.create(second))
        moved = first.copy()
        moved.path = "new/folder/moved.canvas.html"
        await save(Change.update(first, moved))
        assert not (tmp_path / first.path).exists()
        assert moved.id in read_canvas_file(tmp_path / moved.path, tmp_path)

        swapped_first, swapped_second = moved.copy(), second.copy()
        swapped_first.path, swapped_second.path = second.path, moved.path
        await save(
            Change.update(moved, swapped_first), Change.update(second, swapped_second)
        )
        assert first.id in read_canvas_file(tmp_path / swapped_first.path, tmp_path)
        assert second.id in read_canvas_file(tmp_path / swapped_second.path, tmp_path)

        # Fail before and after a rename publishes its new file.
        for after_publish in (False, True):
            current = store.find_one(id=first.id)
            renamed = current.copy()
            renamed.path = f"renamed-{after_publish}.canvas.html"
            other = store.find_one(id=second.id)
            edited = other.copy()
            edited.modified = str(after_publish)
            function = "delete" if after_publish else "create_new"
            original = getattr(file_changes, function)
            failing_path = tmp_path / (current.path if after_publish else renamed.path)

            def fail(path, *args, **kwargs):
                if path == failing_path:
                    raise OSError("write denied")
                return original(path, *args, **kwargs)

            with monkeypatch.context() as patch:
                patch.setattr(file_changes, function, fail)
                with pytest.raises(HTTPException) as error:
                    await save(
                        Change.update(current, renamed), Change.update(other, edited)
                    )
                assert error.value.status_code == 500
            assert store.find_one(id=first.id).path == renamed.path
            assert (
                read_canvas_file(tmp_path / edited.path, tmp_path)[second.id].modified
                == edited.modified
            )
            assert (tmp_path / current.path).exists()
            assert (tmp_path / renamed.path).exists() == after_publish

            retry = renamed.copy()
            retry.modified = f"retry-{after_publish}"
            await save(Change.update(renamed, retry))
            assert (
                read_canvas_file(tmp_path / retry.path, tmp_path)[first.id].modified
                == retry.modified
            )
            assert (tmp_path / current.path).exists() == after_publish
        await dss.close()

    run(check())


@pytest.mark.skipif(os.geteuid() == 0, reason="root can list any folder")
def test_loading_with_problems(dss, tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "scan_project", scan_project)
    page = Page()
    note = dump_to_dict(CardNote(parent_id=page.id, content={"text": "original"}))
    newer = {**note, "content": {"text": "newer"}}
    # A copy saved later wins; older files sharing its page or
    # note id are listed.
    write_canvas(tmp_path / "page.canvas.html", page, [], mtime=2000)
    write_canvas(tmp_path / "page-copy.canvas.html", page, [newer], 3000)
    write_canvas(tmp_path / "other.canvas.html", Page(), [note], mtime=1000)
    write_canvas(tmp_path / "null-notes.canvas.html", Page(), None)
    untyped = dump_to_dict(CardNote(parent_id=page.id))
    del untyped["type_name"]
    write_canvas(tmp_path / "untyped.canvas.html", Page(), [untyped])
    write_canvas(tmp_path / "locked" / "hidden.canvas.html", Page(), [])
    (tmp_path / "locked").chmod(0)
    leftover = tmp_path / ".page.canvas.html.0123456789abcdef.tmp"
    leftover.write_text("interrupted write")

    async def check():
        await dss.load_project("p", tmp_path)
        pfm = dss.project_folder_manager("p")
        assert {e.id for e in pfm.store.find()} == {page.id, note["id"]}
        assert pfm.store.find_one(id=note["id"]).text == "newer"
        status = await routes.get_status()
        problems = {p["path"]: p["kind"] for p in status["problems"]["p"]}
        assert problems == {
            "page.canvas.html": "duplicate_id",
            "other.canvas.html": "duplicate_id",
            "null-notes.canvas.html": "unreadable_file",
            "untyped.canvas.html": "unreadable_file",
            "locked": "unlisted_folder",
        }
        assert leftover.exists()
        await dss.close()

    try:
        run(check())
    finally:
        (tmp_path / "locked").chmod(0o755)


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
