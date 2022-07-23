from collections import defaultdict
from datetime import datetime, timedelta
import json
from pathlib import Path
import sched
import shutil
import threading
import time
from typing import Dict

from misli.entity_library.change import Change
from misli.helpers import get_new_id
from misli.logging import get_logger
from misli.pubsub import Channel
from pamet import desktop_app
import pamet
from pamet.model.page import Page
from pamet.storage.file_system.repository import FSStorageRepository

log = get_logger(__name__)

IGNORE_LOCK = True

RECENT = 'recent'
BACKUP = 'backup'
PERMANENT = 'permanent'

HOUR = 60 * 60
DAY = 24 * HOUR
WEEK = 7 * DAY
LUNAR_MONTH = 4 * WEEK

INTERVAL_FIRST_DAY = 1 * HOUR
INTERVAL_FIRST_MONTH = DAY
INTERVAL_UNTIL_MAX = WEEK

PROCESS_INTERVAL = 30
PRUNE_INTERVAL = DAY
BACKUP_INTERVAL = 1 * HOUR

# Debug
PROCESS_INTERVAL = 5  # 30
PRUNE_INTERVAL = 15
BACKUP_INTERVAL = 10


def datetime_from_path(path):
    parts = path.stem.split('_')
    return datetime.fromisoformat(parts[1])


class Backup:
    def __init__(self, path: Path):
        self.path: Path = path
        self.datetime = datetime_from_path(path)


class BackupService:

    def __init__(self, change_set_channel: Channel,
                 repo: FSStorageRepository) -> None:
        self.id = get_new_id()
        self.fs_repo = repo
        self._changed_page_ids: set = set()

        if not shutil.which('git'):
            raise Exception(
                'The backup service depends on git. Install it please.')
        self.change_set_channel = change_set_channel
        self.change_sub = None

        self.worker_thread = threading.Thread()
        self.scheduler = sched.scheduler(time.time, time.sleep)

        self._change_buffer: list[Change] = []
        self.buffer_lock = threading.Lock()

        config = desktop_app.get_config()
        self.record_all_changes = config.record_all_changes
        self.backup_folder: Path = Path(config.backup_folder)
        self.backup_folder.mkdir(exist_ok=True, parents=True)

        # self._recents_by_page_id = {}
        # self._backups_by_page_id: Dict[str, Path] = defaultdict(list)

    def prune_timestamp_path(self) -> Path:
        return self.backup_folder / 'last_prune_timestamp.txt'

    def backup_timestamp_path(self) -> Path:
        return self.backup_folder / 'last_backup_timestamp.txt'

    def service_lock_path(self) -> Path:
        return self.backup_folder / 'backup_service_lock'

    def all_changes_path(self, page_id) -> Path:
        return self.permanent_backups_folder(page_id>) / 'all_changes.jsonl'

    def recents_path(self, page_id: str) -> Path:
        return self.backup_folder / page_id / 'recent_changes.jsonl'

    def backup_path(self, page_id, dt: datetime = None) -> Path:
        dt = dt or datetime.utcnow()
        path = (self.backup_folder / page_id /
                f'{BACKUP}_{dt.isoformat()}.json')
        return path

    def permanent_backups_folder(self, page_id) -> Path:
        return self.backup_folder / page_id / PERMANENT

    def handle_change_set(self, change_set: list[Change]):
        with self.buffer_lock:
            self._change_buffer.extend(change_set)

    def backup_changed_pages(self):
        print('[BackupService] Doing backup')
        # Move the recent changes to backup files
        for page_id in self._changed_page_ids:
            page = pamet.page(id=page_id)
            notes = page.notes()
            arrows = page.arrows()
            page_str = self.fs_repo.serialize_page(page, notes, arrows)

            path = self.backup_path(page_id)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(page_str)
        self._changed_page_ids.clear()

        self.backup_timestamp_path().write_text(datetime.utcnow().isoformat())

    def page_backup_folders(self):
        for page_folder in self.backup_folder.iterdir():
            if not page_folder.is_dir():
                continue
            yield page_folder

    def prune_all(self):
        print('[BackupService] Pruning backups.')
        for page_folder in self.page_backup_folders():
            self.prune_page_backups(page_folder.name)

    def prune_page_backups(self, page_id):
        now = datetime.utcnow()

        # Sort the backups into bins according to how old they are
        last_day = []
        last_month = []
        last_year = []
        more_than_a_year = []
        page_folder = self.backup_folder / page_id
        for backup_path in page_folder.iterdir():
            if not backup_path.name.startswith(BACKUP) or \
                    not backup_path.is_file() or\
                    backup_path == self.service_lock_path():
                continue

            backup = Backup(backup_path)
            backup_age = now - backup.datetime
            backup_age = backup_age.seconds

            if backup_age < DAY:
                last_day.append(backup)
            elif backup_age < LUNAR_MONTH:
                last_month.append(backup)
            elif backup_age < 366 * DAY:
                last_year.append(backup)
            else:
                more_than_a_year.append(backup)

        # Bin by hour, day, and week (by the clock/calendar),sort, and
        # delete all except the last for each group
        by_hour = defaultdict(list)
        for backup in last_day:
            by_hour[backup.datetime.hour].append(backup)
        by_day = defaultdict(list)
        for backup in last_month:
            by_day[backup.datetime.day].append(backup)
        by_week = defaultdict(list)
        for backup in last_year:
            by_week[backup.datetime.week].append(backup)

        for_removal = []
        for by_interval in [by_hour, by_day, by_week]:  # Just so its DRY
            for specific_time_frame, backups in by_interval.items():
                if len(backups) > 1:
                    # Sort chronologically
                    backups = sorted(backups, key=lambda b: b.datetime)
                    # Remove all except the last
                    for_removal.extend(backups[:-1])

        for backup in for_removal:
            backup.path.unlink()
            log.info(f'Removed backup {backup.path}')

        # For those older than a year - move them to a yearly folder
        # We're assuming they're already cleaned a week apart
        # If not - big deal
        for backup in more_than_a_year:
            folder = backup.path.parent / str(backup.datetime.year)
            folder.mkdir(parents=True, exist_ok=True)
            new_path = folder / backup.path.name
            backup.path.rename(new_path)
            log.info(
                f'Moved backup {backup.path.name} '
                'to the yearly folder {folder}')

        # Update the timestamp
        self.prune_timestamp_path().write_text(now.isoformat())

    def backup_and_reschedule(self):
        self.backup_changed_pages()
        self.scheduler.enter(BACKUP_INTERVAL, 2,
                             self.backup_and_reschedule)

    def prune_and_reschedule(self):
        self.prune_all()
        self.scheduler.enter(PRUNE_INTERVAL, 2,
                             self.prune_and_reschedule)

    def process_changes(self):
        print('[BackupService] Processing changes')
        with self.buffer_lock:
            changes = self._change_buffer
            self._change_buffer = []

        # Sort the changes by page
        changes_by_page = defaultdict(list)
        for change in changes:
            entity = change.last_state()
            page_id = None
            if isinstance(entity, Page):
                page_id = entity.id
            else:
                page_id = entity.page_id

            if not page_id:
                log.error(f'Change f{change} has not page id')
                continue

            changes_by_page[page_id].append(change)

        # Save the ids of the changed pages, so that we know what to back up
        self._changed_page_ids.update(changes_by_page.keys())

        # Record the changes - for research/testing/visualization
        # Normal users wouldn't enable it (I guess?)
        if not self.record_all_changes:
            return

        for page_id, changes in changes_by_page.items():
            json_strings = []
            for change in changes:
                json_str = json.dumps(change.as_safe_delta_dict())
                json_strings.append(json_str + '\n')
            json_str_all = ''.join(json_strings)

            all_changes_path = self.all_changes_path(page_id)
            all_changes_path.parent.mkdir(parents=True, exist_ok=True)
            with open(all_changes_path, 'a') as all_changes_file:
                all_changes_file.write(json_str_all)

    def process_changes_and_reschedule(self):
        self.process_changes()
        self.scheduler.enter(PROCESS_INTERVAL, 1,
                             self.process_changes_and_reschedule)

    def start(self):
        if self.service_lock_path().exists() and not IGNORE_LOCK:
            raise Exception('Another backup service is running. If you\'re'
                            'sure it\'s not - you can delete the lock file: '
                            f'{self.service_lock_path()}')
        self.service_lock_path().write_text(self.id)

        log.info('[BackupService] Starting')

        self.change_sub = self.change_set_channel.subscribe(
            self.handle_change_set)

        # Get the timestamp for the last backup and schedule accordingly
        backup_ts = self.backup_timestamp_path()
        if backup_ts.exists():
            last_backup_dt = datetime.fromisoformat(backup_ts.read_text())
            now = datetime.utcnow()

            # Check if it's time to do a backup
            time_since_last_backup = now - last_backup_dt
            if time_since_last_backup.seconds > BACKUP_INTERVAL:
                self.backup_and_reschedule()
            else:
                backup_delta = timedelta(seconds=BACKUP_INTERVAL)
                time_till_next_backup = backup_delta - time_since_last_backup
                self.scheduler.enter(time_till_next_backup.seconds, 2,
                                     self.backup_and_reschedule)
        else:  # First run
            self.backup_and_reschedule()

        # Get the timestamp for the last pruning and schedule accordingly
        prune_ts = self.prune_timestamp_path()
        if prune_ts.exists():
            last_prune_dt = datetime.fromisoformat(prune_ts.read_text())
            now = datetime.utcnow()

            # Check if it's time to do prunung
            time_since_last_prune = now - last_prune_dt
            if time_since_last_prune.seconds > PRUNE_INTERVAL:
                self.prune_and_reschedule()
            else:
                prune_delta = timedelta(seconds=PRUNE_INTERVAL)
                time_till_next_prune = prune_delta - time_since_last_prune
                self.scheduler.enter(time_till_next_prune.seconds, 2,
                                     self.prune_and_reschedule)
        else:  # First run
            self.prune_and_reschedule()

        # Schedule the processing of changes
        self.scheduler.enter(PROCESS_INTERVAL, 1,
                             self.process_changes_and_reschedule)

        self.worker_thread = threading.Thread(target=self.scheduler.run)
        self.worker_thread.start()

    def stop(self):
        self.change_sub.unsubscribe()

        for event in self.scheduler.queue:
            self.scheduler.cancel(event=event)

        log.info('[BackupService] Cancelled events.')
        self.worker_thread.join()
        log.info('[BackupService] Stopped service.')
        self.service_lock_path().unlink()
