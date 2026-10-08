import asyncio
from datetime import datetime, timedelta
from pathlib import Path

from sivkit.util import current_time, fake_time

from pamet.model.card_note import CardNote
from pamet.model.page import Page
from pamet.services.backup import BackupService, _page_path_stem
from pamet.storage.pamet_in_memory_store import PametInMemoryStore

# Only the first scheduled run happens during a test
BACKUP_INTERVAL = 60
PRUNE_INTERVAL = 60

PAGE_PATH = "test.canvas.html"
PAGE_PATH_STEM = "test"
SUB_PAGE_PATH = "notes/deep.canvas.html"
SUB_PAGE_PATH_STEM = "notes/deep"


def _make_store_with_page(
    page_path: str = PAGE_PATH,
) -> tuple[PametInMemoryStore, Page]:
    store = PametInMemoryStore()
    page = Page(path=page_path)
    store.insert_one(page)
    return store, page


def _add_note(
    store: PametInMemoryStore, page: Page, text: str = "Test note"
) -> CardNote:
    note = CardNote(parent_id=page.id)
    note.text = text
    store.insert_one(note)
    return note


def test_backup_basic(tmp_path):
    """Create a page, mark it changed, back up, and verify a backup file exists."""
    store, page = _make_store_with_page()
    svc = BackupService(backup_folder=tmp_path, store=store)

    svc.mark_pages_changed({page.id})
    svc.backup_changed_pages()

    backups = svc.recent_backups_for_page(PAGE_PATH_STEM)
    assert len(backups) == 1
    assert backups[0].exists()
    assert backups[0].name.endswith(".canvas.html")


def test_backup_subfolder_page(tmp_path):
    """Pages in subfolders get backup dirs mirroring the project structure."""
    store, page = _make_store_with_page(SUB_PAGE_PATH)
    svc = BackupService(backup_folder=tmp_path, store=store)

    svc.mark_pages_changed({page.id})
    svc.backup_changed_pages()

    backups = svc.recent_backups_for_page(SUB_PAGE_PATH_STEM)
    assert len(backups) == 1
    # The backup file should live under backups/notes/deep/
    assert "notes" in backups[0].parts


def test_backup_two_snapshots(tmp_path):
    """Two changed-page cycles produce two backup files."""
    store, page = _make_store_with_page()
    svc = BackupService(backup_folder=tmp_path, store=store)

    svc.mark_pages_changed({page.id})
    svc.backup_changed_pages()

    _add_note(store, page, "second edit")
    svc.mark_pages_changed({page.id})
    with fake_time(time=current_time() + timedelta(seconds=1)):
        svc.backup_changed_pages()

    backups = svc.recent_backups_for_page(PAGE_PATH_STEM)
    assert len(backups) == 2


def test_pruning(tmp_path):
    """Staggered pruning keeps one backup per time bin."""
    store, page = _make_store_with_page()
    svc = BackupService(backup_folder=tmp_path, store=store)

    for_removal: list[Path] = []
    for_keeping: list[Path] = []

    # Initial backup
    initial_time = datetime(
        year=2099, month=7, day=30, hour=23, minute=1, second=0
    ).astimezone()
    with fake_time(initial_time):
        svc.mark_pages_changed({page.id})
        svc.backup_changed_pages()
    for_keeping.append(svc.recent_backup_path(PAGE_PATH_STEM, initial_time))

    # --- Weekly bin: 2 backups in same week, older should be pruned ---
    weekly_deleted_time = datetime.fromisocalendar(
        year=2100, week=10, day=1
    ).astimezone()
    with fake_time(weekly_deleted_time):
        _add_note(store, page, "weekly-1")
        svc.mark_pages_changed({page.id})
        svc.backup_changed_pages()
    for_removal.append(svc.recent_backup_path(PAGE_PATH_STEM, weekly_deleted_time))

    weekly_kept_time = datetime.fromisocalendar(year=2100, week=10, day=2).astimezone()
    with fake_time(weekly_kept_time):
        _add_note(store, page, "weekly-2")
        svc.mark_pages_changed({page.id})
        svc.backup_changed_pages()
    for_keeping.append(svc.recent_backup_path(PAGE_PATH_STEM, weekly_kept_time))

    # --- Daily bin: 2 backups on same day, older should be pruned ---
    daily_deleted_time = datetime(
        year=2100, month=6, day=15, hour=2, minute=1, second=0
    ).astimezone()
    with fake_time(daily_deleted_time):
        _add_note(store, page, "daily-1")
        svc.mark_pages_changed({page.id})
        svc.backup_changed_pages()
    for_removal.append(svc.recent_backup_path(PAGE_PATH_STEM, daily_deleted_time))

    daily_kept_time = datetime(
        year=2100, month=6, day=15, hour=14, minute=1, second=0
    ).astimezone()
    with fake_time(daily_kept_time):
        _add_note(store, page, "daily-2")
        svc.mark_pages_changed({page.id})
        svc.backup_changed_pages()
    for_keeping.append(svc.recent_backup_path(PAGE_PATH_STEM, daily_kept_time))

    # --- Hourly bin: 2 backups in same hour, older should be pruned ---
    hourly_deleted_time = datetime(
        year=2100, month=6, day=30, hour=15, minute=1, second=0
    ).astimezone()
    with fake_time(hourly_deleted_time):
        _add_note(store, page, "hourly-1")
        svc.mark_pages_changed({page.id})
        svc.backup_changed_pages()
    for_removal.append(svc.recent_backup_path(PAGE_PATH_STEM, hourly_deleted_time))

    hourly_kept_time = datetime(
        year=2100, month=6, day=30, hour=15, minute=20, second=0
    ).astimezone()
    with fake_time(hourly_kept_time):
        _add_note(store, page, "hourly-2")
        svc.mark_pages_changed({page.id})
        svc.backup_changed_pages()
    for_keeping.append(svc.recent_backup_path(PAGE_PATH_STEM, hourly_kept_time))

    # --- Past the permanent age: 2 backups in same week, both kept ---
    for day in (1, 2):
        permanent_age_time = datetime.fromisocalendar(
            year=2098, week=10, day=day
        ).astimezone()
        with fake_time(permanent_age_time):
            _add_note(store, page, f"permanent-age-{day}")
            svc.mark_pages_changed({page.id})
            svc.backup_changed_pages()
        for_keeping.append(svc.recent_backup_path(PAGE_PATH_STEM, permanent_age_time))

    # Prune at 2100-06-30 23:01:00
    with fake_time(
        datetime(year=2100, month=6, day=30, hour=23, minute=1, second=0).astimezone()
    ):
        svc.prune_page_backups(PAGE_PATH_STEM)

    assert len(for_keeping) == len(svc.recent_backups_for_page(PAGE_PATH_STEM))

    for path in for_keeping:
        assert path.exists(), f"Expected kept: {path}"
    for path in for_removal:
        assert not path.exists(), f"Expected pruned: {path}"


def test_permanent_storage(tmp_path):
    """Old backups get moved to yearly permanent folders."""
    store, page = _make_store_with_page()
    svc = BackupService(backup_folder=tmp_path, store=store)

    initial_time = datetime(year=2000, month=7, day=30).astimezone()
    with fake_time(initial_time):
        svc.mark_pages_changed({page.id})
        svc.backup_changed_pages()

    svc.move_to_permanent_where_appropriate(PAGE_PATH_STEM)

    assert not svc.recent_backups_for_page(PAGE_PATH_STEM)
    assert svc.permanent_backup_path(PAGE_PATH_STEM, initial_time).exists()


def test_empty_dir_cleanup_on_prune(tmp_path):
    """After pruning removes all backups for a subfolder page, empty dirs are cleaned."""
    store, page = _make_store_with_page(SUB_PAGE_PATH)
    svc = BackupService(backup_folder=tmp_path, store=store)

    # Create a backup then move it to permanent (simulating age)
    t = datetime(year=2000, month=1, day=1).astimezone()
    with fake_time(t):
        svc.mark_pages_changed({page.id})
        svc.backup_changed_pages()

    svc.move_to_permanent_where_appropriate(SUB_PAGE_PATH_STEM)

    # The yearly folder should exist
    yearly_folder = svc.permanent_backups_folder(SUB_PAGE_PATH_STEM, t)
    assert yearly_folder.exists()

    # Now prune_all — the permanent backup is in a yearly folder, not pruned,
    # but the parent page folder is not empty either (it has the yearly subdir).
    # Let's manually remove the permanent backup to simulate full cleanup
    for f in yearly_folder.iterdir():
        f.unlink()

    svc._cleanup_empty_dirs()

    # The notes/ subfolder under backups should be gone
    notes_dir = svc.backup_folder / "notes"
    assert not notes_dir.exists()


def test_backup_task(tmp_path):
    """The task backs up and prunes on start; close flushes pending changes."""
    store, page = _make_store_with_page()
    svc = BackupService(
        backup_folder=tmp_path,
        store=store,
        backup_interval=BACKUP_INTERVAL,
        prune_interval=PRUNE_INTERVAL,
    )

    async def run():
        svc.mark_pages_changed({page.id})
        svc.backups_enabled = True
        while not svc.last_prune_timestamp_path().exists():
            await asyncio.sleep(0.01)
        assert len(svc.recent_backups_for_page(PAGE_PATH_STEM)) == 1

        _add_note(store, page, "pending at close")
        svc.mark_pages_changed({page.id})
        with fake_time(time=current_time() + timedelta(seconds=1)):
            await svc.close()
        assert len(svc.recent_backups_for_page(PAGE_PATH_STEM)) == 2

    asyncio.run(asyncio.wait_for(run(), 10))
