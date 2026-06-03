"""Backup service for v5 desktop storage.

Periodically snapshots changed pages as .canvas backup files with a staggered
versioning scheme.  Designed to be owned per-project by a
ProjectFolderManager and signalled via ``mark_pages_changed()`` whenever the
PFM applies a delta (from frontend edits or FS watcher).

Backup folder layout (inside ``{repo_root}/.pamet/backups/``):
    {page_path_stem}/backup_{timestamp}.canvas   (recent)
    {page_path_stem}/{year}/backup_...canvas      (permanent, >1yr)

Where *page_path_stem* is the page's project-relative path without the
``.canvas`` extension (e.g. ``notes/my-page``).  This mirrors the project
folder structure.  Empty subdirectories are cleaned up on pruning.
"""

from __future__ import annotations

import os
import sched
import threading
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from sivkit.libs.model import dump_to_dict
from sivkit.logging import get_logger
from sivkit.util import current_time, timestamp

from pamet.model.arrow import Arrow
from pamet.model.page import Page
from pamet.services.constants import CANVAS_FILE_EXT
from pamet.storage.canvas_html import dump_canvas_html
from pamet.storage.pamet_in_memory_store import PametInMemoryStore

log = get_logger(__name__)

BACKUP = "backup"

HOUR = 60 * 60
DAY = 24 * HOUR
WEEK = 7 * DAY
LUNAR_MONTH = 4 * WEEK

PERMANENT_BACKUP_AGE = 366 * DAY
BACKUP_INTERVAL = 1 * HOUR
PRUNE_INTERVAL = DAY

TIME_FORMAT = "%Y-%m-%dT%H-%M-%S%z"


def datetime_from_backup_path(path: Path) -> datetime:
    """Extracts the timestamp from the path/name of a backup file."""
    stem = path.stem  # e.g. backup_2026-03-18T18-50-12+0200
    parts = stem.split("_", 1)
    ts = parts[1]
    return datetime.strptime(ts, TIME_FORMAT)


def file_timestamp(dt: datetime) -> str:
    return dt.strftime(TIME_FORMAT)


def _page_path_stem(page_path: str) -> str:
    """Return the page's project-relative path without the .canvas extension."""
    if page_path.endswith(CANVAS_FILE_EXT):
        return page_path[: -len(CANVAS_FILE_EXT)]
    return page_path


def _remove_empty_parents(path: Path, stop_at: Path) -> None:
    """Remove *path* and its empty ancestors up to (but not including) *stop_at*."""
    current = path
    while current != stop_at:
        try:
            current.rmdir()  # Only succeeds if empty
        except OSError:
            break
        current = current.parent


class Backup:
    """A minimal convenience class for backup files."""

    def __init__(self, path: Path):
        self.path: Path = path
        self.datetime = datetime_from_backup_path(path)


class BackupService:
    """Per-project backup service for v5 desktop storage.

    The service is always instantiated (even when backups_enabled=False) so
    that existing backups can be queried by the frontend.  Creation of new
    backups and scheduling only happens while ``backups_enabled`` is True.

    Changed page IDs are fed in via ``mark_pages_changed()``—called by the
    PFM whenever a delta is applied.  The worker thread periodically
    snapshots those pages and prunes old backups.
    """

    def __init__(
        self,
        backup_folder: Path,
        store: PametInMemoryStore,
        backup_interval: float = BACKUP_INTERVAL,
        prune_interval: float = PRUNE_INTERVAL,
        permanent_backup_age: float = PERMANENT_BACKUP_AGE,
    ) -> None:
        self.backup_folder: Path = Path(backup_folder)
        self.store = store

        self.backup_interval = backup_interval
        self.prune_interval = prune_interval
        self.permanent_backup_age = permanent_backup_age

        self._changed_page_ids: set[str] = set()
        self._lock = threading.Lock()

        self._backups_enabled = False
        self.stop_event = threading.Event()
        self.worker_thread: threading.Thread | None = None
        self.scheduler = sched.scheduler(time.time, time.sleep)

        # Ensure top-level backup directory exists
        self.backup_folder.mkdir(exist_ok=True, parents=True)

    # -- Properties ------------------------------------------------------------

    @property
    def backups_enabled(self) -> bool:
        return self._backups_enabled

    @backups_enabled.setter
    def backups_enabled(self, value: bool) -> None:
        if value == self._backups_enabled:
            return
        self._backups_enabled = value
        if value:
            self.start()
        else:
            self.stop()

    # -- Path helpers ----------------------------------------------------------

    def last_prune_timestamp_path(self) -> Path:
        return self.backup_folder / "last_prune_timestamp.txt"

    def last_backup_timestamp_path(self) -> Path:
        return self.backup_folder / "last_backup_timestamp.txt"

    def page_backup_folder(self, page_path_stem: str) -> Path:
        return self.backup_folder / page_path_stem

    def recent_backup_path(self, page_path_stem: str, dt: datetime) -> Path:
        name = f"{BACKUP}_{file_timestamp(dt)}{CANVAS_FILE_EXT}"
        return self.page_backup_folder(page_path_stem) / name

    def permanent_backups_folder(self, page_path_stem: str, dt: datetime) -> Path:
        return self.page_backup_folder(page_path_stem) / str(dt.year)

    def permanent_backup_path(self, page_path_stem: str, dt: datetime) -> Path:
        name = f"{BACKUP}_{file_timestamp(dt)}{CANVAS_FILE_EXT}"
        return self.permanent_backups_folder(page_path_stem, dt) / name

    def _page_path_stem_for_id(self, page_id: str) -> str | None:
        """Look up the page path stem for a given page ID from the store."""
        page = self.store.find_one(id=page_id)
        if page is None or not isinstance(page, Page):
            return None
        return _page_path_stem(page.path)

    # -- Enumeration -----------------------------------------------------------

    def _iter_page_backup_folders(self):
        """Walk the backup tree and yield (page_path_stem, folder_path) for
        every leaf directory that contains backup files."""
        root = self.backup_folder
        if not root.exists():
            return
        for dirpath, _dirnames, filenames in os.walk(root):
            has_backups = any(f.startswith(BACKUP) for f in filenames)
            if has_backups:
                rel = Path(dirpath).relative_to(root).as_posix()
                yield rel, Path(dirpath)

    def recent_backups_for_page(self, page_path_stem: str) -> list[Path]:
        folder = self.page_backup_folder(page_path_stem)
        if not folder.exists():
            return []
        backups = [
            f for f in folder.iterdir() if f.is_file() and f.name.startswith(BACKUP)
        ]
        return sorted(backups, key=lambda b: datetime_from_backup_path(b))

    def all_backups_for_page(self, page_path_stem: str) -> list[Path]:
        folder = self.page_backup_folder(page_path_stem)
        if not folder.exists():
            return []
        backups = []
        for dirpath, _dirnames, filenames in os.walk(folder):
            for fname in filenames:
                if fname.startswith(BACKUP):
                    backups.append(Path(dirpath) / fname)
        return sorted(backups, key=lambda b: datetime_from_backup_path(b))

    def last_backup_time(self, page_path_stem: str) -> datetime | None:
        all_backups = self.all_backups_for_page(page_path_stem)
        if all_backups:
            return datetime_from_backup_path(all_backups[-1])
        return None

    # -- Signalling ------------------------------------------------------------

    def mark_pages_changed(self, page_ids: set[str]) -> None:
        """Called by PFM after applying a delta.  Thread-safe."""
        with self._lock:
            self._changed_page_ids.update(page_ids)

    # -- Backup creation -------------------------------------------------------

    def _serialize_page(self, page_id: str) -> str | None:
        """Serialize a page and its children as a .canvas HTML string."""
        page = self.store.find_one(id=page_id)
        if page is None or not isinstance(page, Page):
            return None

        page_dict = dump_to_dict(page)
        notes: list[dict] = []
        arrows: list[dict] = []

        for child in self.store.find(parent_id=page_id):
            child_dict = dump_to_dict(child)
            if isinstance(child, Arrow):
                arrows.append(child_dict)
            else:
                notes.append(child_dict)

        file_data = dict(page_dict)
        file_data.pop("path", None)
        file_data["notes"] = notes
        file_data["arrows"] = arrows

        return dump_canvas_html(file_data)

    def backup_changed_pages(self) -> None:
        """Snapshot all pages marked as changed."""
        with self._lock:
            page_ids = self._changed_page_ids.copy()
            self._changed_page_ids.clear()

        if not page_ids:
            return

        for page_id in page_ids:
            page = self.store.find_one(id=page_id)
            if page is None or not isinstance(page, Page):
                continue

            page_path_stem = _page_path_stem(page.path)
            page_str = self._serialize_page(page_id)
            if page_str is None:
                continue

            now = current_time()
            backup_file_path = self.recent_backup_path(page_path_stem, now)
            backup_file_path.parent.mkdir(parents=True, exist_ok=True)

            if backup_file_path.exists():
                log.warning("Backup file already exists at %s", backup_file_path)

            backup_file_path.write_text(page_str, encoding="utf-8")
            log.info("Backed up page %s → %s", page_id, backup_file_path)

        self.last_backup_timestamp_path().write_text(timestamp(current_time()))

    # -- Pruning ---------------------------------------------------------------

    def move_to_permanent_where_appropriate(self, page_path_stem: str) -> None:
        folder = self.page_backup_folder(page_path_stem)
        if not folder.exists():
            return

        for file_path in list(folder.iterdir()):
            if not file_path.name.startswith(BACKUP) or not file_path.is_file():
                continue

            backup = Backup(file_path)
            backup_age = (current_time() - backup.datetime).total_seconds()

            if backup_age > self.permanent_backup_age:
                dest_folder = self.permanent_backups_folder(
                    page_path_stem, backup.datetime
                )
                dest_folder.mkdir(parents=True, exist_ok=True)
                new_path = dest_folder / backup.path.name
                backup.path.rename(new_path)
                log.info(
                    "Moved backup %s to yearly folder %s",
                    backup.path.name,
                    dest_folder,
                )

    def prune_page_backups(self, page_path_stem: str) -> None:
        """Prune old backups using the staggered versioning scheme:
        - 1 per hour for the last day
        - 1 per day for the last month
        - 1 per week until permanent age
        """
        now = current_time()
        folder = self.page_backup_folder(page_path_stem)
        if not folder.exists():
            return

        last_day: list[Backup] = []
        last_month: list[Backup] = []
        older_than_a_month: list[Backup] = []

        for file_path in folder.iterdir():
            if not file_path.name.startswith(BACKUP) or not file_path.is_file():
                continue

            backup = Backup(file_path)
            age_seconds = (now - backup.datetime).total_seconds()

            if age_seconds < DAY:
                last_day.append(backup)
            elif age_seconds < LUNAR_MONTH:
                last_month.append(backup)
            elif age_seconds < self.permanent_backup_age:
                older_than_a_month.append(backup)

        by_hour: dict[int, list[Backup]] = defaultdict(list)
        for b in last_day:
            by_hour[b.datetime.hour].append(b)

        by_day: dict[int, list[Backup]] = defaultdict(list)
        for b in last_month:
            by_day[b.datetime.day].append(b)

        by_year_and_week: dict[tuple, list[Backup]] = defaultdict(list)
        for b in older_than_a_month:
            year, week, _ = b.datetime.isocalendar()
            by_year_and_week[(year, week)].append(b)

        for by_interval in [by_hour, by_day, by_year_and_week]:
            for _time_frame, backups in by_interval.items():
                if len(backups) <= 1:
                    continue
                backups.sort(key=lambda b: b.datetime)
                for backup in backups[:-1]:
                    backup.path.unlink()
                    log.info("Pruned backup %s", backup.path)

    def prune_all(self) -> None:
        """Prune backups for all pages and clean up empty directories."""
        for page_path_stem, _folder in list(self._iter_page_backup_folders()):
            # Skip yearly/permanent subdirs (they're children of page folders)
            # We only prune the top-level page_path_stem folders
            self.prune_page_backups(page_path_stem)
            self.move_to_permanent_where_appropriate(page_path_stem)

        # Clean up empty directories
        self._cleanup_empty_dirs()

        self.last_prune_timestamp_path().write_text(timestamp(current_time()))

    def _cleanup_empty_dirs(self) -> None:
        """Remove empty subdirectories under the backups root."""
        root = self.backup_folder
        if not root.exists():
            return
        # Walk bottom-up so children are cleaned before parents
        for dirpath, dirnames, filenames in os.walk(root, topdown=False):
            dir_p = Path(dirpath)
            if dir_p == root:
                continue
            if not filenames and not dirnames:
                _remove_empty_parents(dir_p, root)

    # -- Scheduling ------------------------------------------------------------

    def _backup_and_reschedule(self) -> None:
        self.backup_changed_pages()
        self.scheduler.enter(self.backup_interval, 2, self._backup_and_reschedule)

    def _prune_and_reschedule(self) -> None:
        self.prune_all()
        self.scheduler.enter(self.prune_interval, 2, self._prune_and_reschedule)

    def _run_scheduler(self) -> None:
        timeout = 1
        while timeout and timeout > 0:
            timeout = self.scheduler.run(blocking=False)
            self.stop_event.wait(timeout)

    def start(self) -> None:
        """Start the backup worker thread."""
        if self.worker_thread is not None and self.worker_thread.is_alive():
            return

        log.info("Starting backup service for %s", self.backup_folder)
        self.stop_event.clear()

        # Schedule backup based on last backup timestamp
        backup_delay = 0.0
        backup_ts_path = self.last_backup_timestamp_path()
        if backup_ts_path.exists():
            try:
                ts_text = backup_ts_path.read_text().strip()
                if ts_text:
                    last_backup_dt = datetime.fromisoformat(ts_text)
                    elapsed = (current_time() - last_backup_dt).total_seconds()
                    if elapsed < self.backup_interval:
                        backup_delay = self.backup_interval - elapsed
            except (ValueError, OSError) as e:
                log.warning(
                    "Could not parse last backup timestamp, "
                    "scheduling immediate backup: %s",
                    e,
                )
        self.scheduler.enter(backup_delay, 2, self._backup_and_reschedule)

        # Schedule pruning based on last prune timestamp
        prune_delay = 0.0
        prune_ts_path = self.last_prune_timestamp_path()
        if prune_ts_path.exists():
            try:
                ts_text = prune_ts_path.read_text().strip()
                if ts_text:
                    last_prune_dt = datetime.fromisoformat(ts_text)
                    elapsed = (current_time() - last_prune_dt).total_seconds()
                    if elapsed < self.prune_interval:
                        prune_delay = self.prune_interval - elapsed
            except (ValueError, OSError) as e:
                log.warning(
                    "Could not parse last prune timestamp, "
                    "scheduling immediate prune: %s",
                    e,
                )
        self.scheduler.enter(prune_delay, 2, self._prune_and_reschedule)

        self.worker_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.worker_thread.start()

    def stop(self) -> None:
        """Stop the backup worker thread."""
        for event in list(self.scheduler.queue):
            try:
                self.scheduler.cancel(event)
            except ValueError:
                pass

        self.stop_event.set()
        if self.worker_thread is not None and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5)
        self.worker_thread = None

        log.info("Stopped backup service for %s", self.backup_folder)
