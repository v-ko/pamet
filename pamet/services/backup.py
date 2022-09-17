from collections import defaultdict
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import sched
import shutil
import threading
import time
from typing import List

from peewee import Model, CharField, SqliteDatabase, DateTimeField

from fusion.libs.entity.change import Change
from fusion.util import get_new_id, current_time, timestamp
from fusion.logging import get_logger
from fusion.libs.channel import Channel

from pamet.model.page import Page
from pamet.storage.base_repository import PametRepository
from pamet.storage.file_system.repository import FSStorageRepository

log = get_logger(__name__)

IGNORE_LOCK = False

RECENT = 'recent'
BACKUP = 'backup'
BACKUPS = 'backups'
CHANGESET = 'changeset'
PERMANENT = 'permanent'

HOUR = 60 * 60
DAY = 24 * HOUR
WEEK = 7 * DAY
LUNAR_MONTH = 4 * WEEK

INTERVAL_FIRST_DAY = 1 * HOUR
INTERVAL_FIRST_MONTH = DAY
INTERVAL_UNTIL_MAX = WEEK
PERMANENT_BACKUP_AGE = 366 * DAY

PROCESS_INTERVAL = 30
PRUNE_INTERVAL = DAY
BACKUP_INTERVAL = 1 * HOUR

TIME_FORMAT = '%Y-%m-%dT%H-%M-%S+%z'


def datetime_from_backup_path(path) -> datetime:
    """Exctracts the timestamp from the path/name of a backup file."""
    parts = path.stem.split('_')
    return datetime.strptime(parts[1], TIME_FORMAT)


def datetimes_from_changeset_path(path: Path) -> datetime:
    """Extracts the datetime (start/end) timestamps from a 'changest' file
    path.
    """
    parts = path.stem.split('_')
    return datetime.fromisoformat(parts[1]), datetime.fromisoformat(parts[2])


def file_timestamp(time: datetime):
    return time.strftime(TIME_FORMAT)


class Backup:
    """A minimal convenince class for backup files."""

    def __init__(self, path: Path):
        self.path: Path = path
        self.datetime = datetime_from_backup_path(path)


class ChangePW(Model):
    page_id = CharField()
    time = DateTimeField()
    json = CharField()

    def to_change(self):
        change_dict = json.loads(self.json)
        change = Change.from_safe_delta_dict(change_dict)
        return change


class AnotherServiceAlreadyRunningException(Exception):
    pass


class FSStorageBackupService:
    """Handles creating backups periodically. It has a
    staggered versioning scheme and the option to keep all changes in between
    backups.

    The service connects to the per-TLA changes channel (i.e. receives
    change-sets on every user action. These changes are stored in the
    thread-safe _change_buffer and periodically saved to disk at a
    page-specific tmp_changeset_path.
     This action (done in self.process_changes), backup_changed_pages and
     prune_all are scheduled and executed in a worker thread.

     Backing up saves the changed pages in the respective backup folders and
     moves the change objects (stored in tmp_changeset_file) to a changeset
     file which has the to/from timestamps in it's name.

     Pruning removes backup files according to a staggered versioning scheme.
    I.e. we keep 1 backup for every hour of the first day, 1 per day for the
    first week and one per week after that. When pruning backups - the
    changeset files inbetween get merged.

    Backups older than the PERMANENT_BACKUP_AGE (1 year) get moved to a yearly
    folder (along with the changeset files).

    The backup service has a locking mechanism with a file to avoid running
    multiple services. But that may change in the future.

    Timestamps of the last pruning and last backup operations are kept as files
    in order to schedule the next respective operation correctly.

    The backups are stored in per-page folders. Inside them old/permanent
    backups and changes are stored in per year folders.
     """

    def __init__(self,
                 backup_folder: Path,
                 repository: PametRepository = None,
                 changeset_channel: Channel = None,
                 record_all_changes: bool = False,
                 process_interval: float = PROCESS_INTERVAL,
                 backup_interval: float = BACKUP_INTERVAL,
                 prune_interval: float = PRUNE_INTERVAL,
                 permanent_backup_age: float = PERMANENT_BACKUP_AGE) -> None:
        self.id = get_new_id()

        self.backup_folder: Path = Path(backup_folder)
        self.repo = repository
        self.changeset_channel = changeset_channel
        self.record_all_changes = record_all_changes
        self.changeset_db = None

        self.process_interval = process_interval
        self.backup_interval = backup_interval
        self.prune_interval = prune_interval
        self.permanent_backup_age = permanent_backup_age

        self._changed_page_ids: set = set()
        self.stop_event = threading.Event()

        self.input_channel_sub = None

        self.worker_thread = threading.Thread()
        self.scheduler = sched.scheduler(time.time, time.sleep)

        self._change_buffer: list[Change] = []
        self.buffer_lock = threading.Lock()

        # Prep folders and changeset DB
        self.pages_backup_data_folder().mkdir(exist_ok=True, parents=True)

        if self.record_all_changes:
            self.changeset_db = SqliteDatabase(self.changeset_sqlite_db_path())
            # If the changeset database doesn't exist - create it
            if not self.changeset_sqlite_db_path().exists():

                with self.changeset_db.bind_ctx([ChangePW]):
                    self.changeset_db.create_tables([ChangePW])

    def changeset_sqlite_db_path(self) -> Path:
        return self.backup_folder / 'all_changes.sqlite3'

    def last_prune_timestamp_path(self) -> Path:
        return self.backup_folder / 'last_prune_timestamp.txt'

    def last_backup_timestamp_path(self) -> Path:
        return self.backup_folder / 'last_backup_timestamp.txt'

    def service_lock_path(self) -> Path:
        return self.backup_folder / 'backup_service_lock'

    def pages_backup_data_folder(self):
        return self.backup_folder / BACKUPS

    def page_backup_folder(self, page_id: str) -> Path:
        return self.pages_backup_data_folder() / page_id

    def tmp_changeset_path(self, page_id) -> Path:
        return self.page_backup_folder(page_id) / 'tmp_changeset.jsonl'

    def recent_backup_path(self, page_id, time: datetime) -> Path:
        name = f'{BACKUP}_{file_timestamp(time)}.json'
        return self.page_backup_folder(page_id) / name

    def permanent_backups_folder(self, page_id, time: datetime) -> Path:
        return self.page_backup_folder(page_id) / str(time.year)

    def permanent_backup_path(self, page_id, time: datetime) -> Path:
        name = f'{BACKUP}_{file_timestamp(time)}.json'
        return self.permanent_backups_folder(page_id, time) / name

    # def changeset_path(self, page_id, from_time: datetime,
    #                    to_time: datetime) -> Path:
    #     from_timestamp = timestamp(from_time)
    #     to_timestamp = timestamp(to_time)
    #     file_name = f'{CHANGESET}_{from_timestamp}_{to_timestamp}.jsonl'
    #     path = self.page_backup_folder(page_id) / file_name
    #     return path

    def per_page_backup_folders(self):
        for page_folder in self.pages_backup_data_folder().iterdir():
            if not page_folder.is_dir():
                continue
            yield page_folder

    def backups_for_page(self, page_id) -> list[Path]:
        backups = []
        for root, dirs, files in os.walk(self.page_backup_folder(page_id)):
            for file in files:
                file = Path(file)
                if file.name.startswith(BACKUP):
                    backups.append(file)

        return sorted(backups, key=lambda b: datetime_from_backup_path(b))

    # def existing_backup_path(self, page_id: str, time: datetime):
    #     recent_backup = self.recent_backup_path(page_id, time)
    #     if recent_backup.exists():
    #         return recent_backup

    #     permanent_backup = self.permanent_backup_path(page_id, time)
    #     if permanent_backup.exists():
    #         return permanent_backup

    #     return None

    def recent_backups_for_page(self, page_id) -> List[Path]:
        page_backup_folder = self.page_backup_folder(page_id)
        if not page_backup_folder.exists():
            return []

        backups = []
        for file in page_backup_folder.iterdir():
            if not file.name.startswith(BACKUP):
                continue
            backups.append(file)

        return sorted(backups, key=lambda b: datetime_from_backup_path(b))

    def changeset_paths_for_page(self, page_id) -> List[Path]:
        page_backup_folder = self.page_backup_folder(page_id)
        if not page_backup_folder.exists():
            return []

        changeset_files = []
        for file in page_backup_folder.iterdir():
            if not file.name.startswith(CHANGESET):
                continue
            changeset_files.append(file)

        return sorted(changeset_files,
                      key=lambda b: datetimes_from_changeset_path(b)[0])

    # def last_backup_time(self, page_id: str) -> datetime:
    #     """Returns the timestamp of the most recent backup for a page as a
    #     datetime object."""

    #     last_timestamp = None
    #     for file in self.recent_backups_for_page(page_id):
    #         backup_dt = datetime_from_backup_path(file)
    #         if not last_timestamp:
    #             last_timestamp = backup_dt
    #         elif last_timestamp < backup_dt:
    #             last_timestamp = backup_dt

    #     return last_timestamp

    def last_backup_for_page(self, page_id) -> Path:
        recent_backups = self.recent_backups_for_page(page_id)
        if recent_backups:
            return recent_backups[-1]

        all_backups = self.backups_for_page(page_id)
        if all_backups:
            return all_backups[-1]

        return None

    def last_backup_time(self, page_id: str) -> datetime:
        """Returns the timestamp of the most recent backup for a page as a
        datetime object."""
        last_backup_path = self.last_backup_for_page(page_id)
        if last_backup_path:
            return datetime_from_backup_path(last_backup_path)
        else:
            return None

    def handle_change_set(self, change_set: list[Change]):
        """Should be connected to the per-TLA channel. Adds the received
        changes to the _change_buffer in a thread safe manner."""
        with self.buffer_lock:
            self._change_buffer.extend(change_set)

    def process_changes(self):
        """Sorts the received changes by page id. Stores the ids of pages with
        changes in order to later do backup """
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
                log.error(f'Change f{change} has no page id')
                continue

            changes_by_page[page_id].append(change)

        # Save the ids of the changed pages, so that we know what to back up
        self._changed_page_ids.update(changes_by_page.keys())

        for page_id, changes in changes_by_page.items():
            json_strings = []
            for change in changes:
                json_str = json.dumps(change.as_safe_delta_dict(),
                                      ensure_ascii=False)
                json_strings.append(json_str + '\n')
            json_str_all = ''.join(json_strings)

            tmp_changeset_path = self.tmp_changeset_path(page_id)
            tmp_changeset_path.parent.mkdir(parents=True, exist_ok=True)
            with open(tmp_changeset_path, 'a') as tmp_changeset_file:
                tmp_changeset_file.write(json_str_all)

    def backup_changed_pages(self):
        """Saves the pages marked as changes (in self._changed_page_ids) as
        backup copies and if configured to do so - also saves the change
        objects in files between backups in order to have a fill history."""

        if not self.repo:
            raise Exception('Cannot backup without a configured repository.')

        self.process_changes()  # In case of last second changes

        # Move the recent changes to backup files
        for page_id in self._changed_page_ids:
            # Serialize the page
            page = self.repo.page(page_id)
            if not page:
                # Assume page has been deleted (we don't track that here)
                continue

            notes = self.repo.notes(page)
            arrows = self.repo.arrows(page)
            page_str = FSStorageRepository.serialize_page(page, notes, arrows)

            # Create the backup file
            now = current_time()
            backup_file_path = self.recent_backup_path(page_id, now)
            backup_file_path.parent.mkdir(parents=True, exist_ok=True)
            if backup_file_path.exists():
                error_msg = f'A file already exists at {backup_file_path}'
                log.warning(error_msg)
            backup_file_path.write_text(page_str)

            # If configured to do so - save the changes
            if not self.record_all_changes:
                continue

            # Read them from the tmp changes file, and add them to the db
            tmp_changeset_file = self.tmp_changeset_path(page_id)
            lines = tmp_changeset_file.read_text().splitlines()
            with self.changeset_db.bind_ctx([ChangePW]):
                with self.changeset_db.atomic():
                    for change_json in lines:
                        change = Change.from_safe_delta_dict(
                            json.loads(change_json))
                        change = ChangePW.create(page_id=page_id,
                                                 time=change.time,
                                                 json=change_json)
            tmp_changeset_file.unlink()

        self._changed_page_ids.clear()
        self.last_backup_timestamp_path().write_text(timestamp(current_time()))

    def move_to_permanent_where_appropriate(self, page_id: str):
        # For those older than self.permanent_backup_age -
        # move them to a yearly folder
        page_folder = self.page_backup_folder(page_id)

        for_permanent_backup = []
        for file_path in page_folder.iterdir():
            if not file_path.name.startswith(BACKUP) or \
                    not file_path.is_file():
                continue

            backup = Backup(file_path)
            backup_age = current_time() - backup.datetime

            if backup_age.total_seconds() > self.permanent_backup_age:
                for_permanent_backup.append(backup)

        # Prep the changes file paths and to_times
        changeset_paths_by_to_times = {}
        for file_path in self.page_backup_folder(page_id).iterdir():
            if file_path.name.startswith(CHANGESET):
                from_time, to_time = datetimes_from_changeset_path(file_path)
                changeset_paths_by_to_times[to_time] = file_path

        # We're assuming they're already cleaned a week apart
        # If not - big deal
        for backup in for_permanent_backup:
            folder = self.permanent_backups_folder(page_id, backup.datetime)
            folder.mkdir(parents=True, exist_ok=True)
            new_path = folder / backup.path.name
            backup.path.rename(new_path)
            log.info(f'Moved backup {backup.path.name} '
                     f'to the yearly folder {folder}')

            # # Also move the corresponding changes file if any
            # changeset_path = changeset_paths_by_to_times.get(backup.datetime)
            # if changeset_path:
            #     changeset_path.rename(folder / changeset_path.name)

    def prune_all(self):
        """Calls the pruning method for all pages."""
        # for page_folder in self.per_page_backup_folders():
        #     self.prune_page_backups(page_folder.name)
        #     self.move_to_permanent_where_appropriate(page_folder.name)
        for page_folder in self.per_page_backup_folders():
            page_id = page_folder.name
            self.prune_page_backups(page_id)

            self.move_to_permanent_where_appropriate(page_id)
        self.last_prune_timestamp_path().write_text(timestamp(current_time()))

    def prune_page_backups(self, page_id):
        """Removes old backups in accordance to the staggered scheme and
        configured intervals for each respective period. By default those are:
        Once per hour for the first day.
        Once per day for the first week.
        Once per week until the end of time.
        Also backups older than the PERMANENT_BACKUP_AGE are considered
        permanent and are moved to a per-year folder. Those are not iterated
        over while pruning.
        """
        now = current_time()

        # Sort the backups into bins according to how old they are
        last_day = []
        last_month = []
        older_than_a_month = []
        page_folder = self.page_backup_folder(page_id)
        for file_path in page_folder.iterdir():
            if not file_path.name.startswith(BACKUP) or \
                    not file_path.is_file():
                continue

            backup = Backup(file_path)
            backup_age = now - backup.datetime
            backup_age = backup_age.total_seconds()

            if backup_age < DAY:
                last_day.append(backup)
            elif backup_age < LUNAR_MONTH:
                last_month.append(backup)
            elif backup_age < self.permanent_backup_age:
                older_than_a_month.append(backup)

        # Bin by hour, day, and week (by the clock/calendar),sort, and
        # delete all except the last for each group
        by_hour = defaultdict(list)
        for backup in last_day:
            by_hour[backup.datetime.hour].append(backup)
        by_day = defaultdict(list)
        for backup in last_month:
            by_day[backup.datetime.day].append(backup)
        by_year_and_week = defaultdict(list)
        for backup in older_than_a_month:
            year, week, _ = backup.datetime.isocalendar()
            by_year_and_week[(year, week)].append(backup)

        for_removal = []
        for_keeping = []
        for by_interval in [by_hour, by_day, by_year_and_week]:
            for specific_time_frame, backups in by_interval.items():
                if not backups:
                    continue

                if len(backups) > 1:
                    # Sort chronologically
                    backups = sorted(backups, key=lambda b: b.datetime)

                    # Remove all except the last
                    for_removal.extend(backups[:-1])

                for_keeping.append(backups[-1])

        # Delete the backups files marked for removal
        for backup in for_removal:
            backup.path.unlink()
            log.info(f'Pruned backup {backup.path}')

    def backup_and_reschedule(self):
        self.backup_changed_pages()
        self.scheduler.enter(self.backup_interval, 2,
                             self.backup_and_reschedule)

    def prune_and_reschedule(self):
        self.prune_all()
        self.scheduler.enter(self.prune_interval, 2, self.prune_and_reschedule)

    def process_changes_and_reschedule(self):
        self.process_changes()
        self.scheduler.enter(self.process_interval, 1,
                             self.process_changes_and_reschedule)

    def run_scheduler(self):
        """Execute scheduled operations.

        This gets called in a separate thread. Continues until the stop_event
        is set."""
        timeout = 1
        while timeout and timeout > 0:
            timeout = self.scheduler.run(blocking=False)
            self.stop_event.wait(timeout)

    def start(self):
        """Starts the backup service.

        The startup process includes checking for a service lock, connecting to
        the changes channel, reading the backup storage for per-page changes
        that have not yet been backed up, and reading the last backup and
        prune timestamps.
        The latter are used to schedule backup and pruning operations at the
        time.

        Then the worker thread is started to carry out event scheduling and
        rescheduling."""
        if self.service_lock_path().exists() and not IGNORE_LOCK:
            raise AnotherServiceAlreadyRunningException
            # This should be a notification when I add notifications
            # raise Exception('Another backup service is running. If you\'re'
            #                 'sure it\'s not - you can delete the lock file: '
            #                 f'{self.service_lock_path()}')
        self.service_lock_path().write_text(self.id)

        log.info('Starting')

        # Setup the receival of changes from the change channel if one is given
        if self.changeset_channel:
            self.input_channel_sub = self.changeset_channel.subscribe(
                self.handle_change_set)

        # Search for tmp_changeset files to populate the _changed_page_ids.
        # I.e. figure out which pages expect a backup because some changes
        # were made before the scheduled backup
        for page_backup_folder in self.per_page_backup_folders():
            page_id = page_backup_folder.name
            if self.tmp_changeset_path(page_id).exists():
                self._changed_page_ids.add(page_id)

        # Get the timestamp for the last backup and schedule accordingly
        backup_ts = self.last_backup_timestamp_path()
        if backup_ts.exists():
            last_backup_dt = datetime.fromisoformat(backup_ts.read_text())
            now = current_time()

            # Check if it's time to do a backup
            time_since_last_backup = now - last_backup_dt
            if time_since_last_backup.total_seconds() > self.backup_interval:
                self.backup_and_reschedule()
            else:
                backup_delta = timedelta(seconds=self.backup_interval)
                time_till_next_backup = backup_delta - time_since_last_backup
                self.scheduler.enter(time_till_next_backup.total_seconds(), 2,
                                     self.backup_and_reschedule)
        else:  # First run
            self.backup_and_reschedule()

        # Get the timestamp for the last pruning and schedule accordingly
        prune_ts = self.last_prune_timestamp_path()
        if prune_ts.exists():
            last_prune_dt = datetime.fromisoformat(prune_ts.read_text())
            now = current_time()

            # Check if it's time to do prunung
            time_since_last_prune = now - last_prune_dt
            if time_since_last_prune.total_seconds() > self.prune_interval:
                self.prune_and_reschedule()
            else:
                prune_delta = timedelta(seconds=self.prune_interval)
                time_till_next_prune = prune_delta - time_since_last_prune
                self.scheduler.enter(time_till_next_prune.total_seconds(), 2,
                                     self.prune_and_reschedule)
        else:  # First run
            self.prune_and_reschedule()

        # Schedule the processing of changes
        self.scheduler.enter(self.process_interval, 1,
                             self.process_changes_and_reschedule)

        self.worker_thread = threading.Thread(target=self.run_scheduler)
        self.worker_thread.start()

    def stop(self):
        """Stops the worker thread and unsubscribes from changes."""
        if self.input_channel_sub:
            self.input_channel_sub.unsubscribe()

        for event in self.scheduler.queue:
            self.scheduler.cancel(event=event)
        log.info('Cancelled events.')

        self.stop_event.set()
        self.worker_thread.join()

        if self.service_lock_path().exists():
            self.service_lock_path().unlink()
        log.info('Stopped service.')

    def get_changes(self,
                    page_id: str = None,
                    after_time: datetime = None,
                    before_time: datetime = None):
        with self.changeset_db.bind_ctx([ChangePW]):
            where_args = []
            if page_id is not None:
                where_args.append(ChangePW.page_id == page_id)
            if after_time is not None:
                where_args.append(ChangePW.time >= after_time)
            if before_time is not None:
                where_args.append(ChangePW.time < before_time)

            query = ChangePW.select()
            if where_args:
                query = query.where(*where_args)

            for change_pw in query.iterator():
                yield change_pw.to_change()
