from collections import defaultdict
from datetime import datetime, timedelta
import json
from pathlib import Path
import sched
import shutil
import threading
import time
from typing import Generator, List, Tuple

from misli.entity_library.change import Change
from misli.helpers import get_new_id, current_time, timestamp
from misli.logging import get_logger
from misli.pubsub import Channel

import pamet
from pamet.model.page import Page
from pamet.storage.file_system.repository import FSStorageRepository
from pamet import desktop_app

log = get_logger(__name__)

IGNORE_LOCK = True

RECENT = 'recent'
BACKUP = 'backup'
CHANGES = 'changes'
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


def datetime_from_backup_path(path) -> datetime:
    """Exctracts the timestamp from the path/name of a backup file."""
    parts = path.stem.split('_')
    return datetime.fromisoformat(parts[1])


def datetimes_from_changes_path(path: Path) -> datetime:
    """Extracts the datetime (start/end) timestamps from a 'changes' file path.
    """
    parts = path.stem.split('_')
    return datetime.fromisoformat(parts[1]), datetime.fromisoformat(parts[2])


class Backup:
    """A minimal convenince class for backup files."""

    def __init__(self, path: Path):
        self.path: Path = path
        self.datetime = datetime_from_backup_path(path)


class FSStorageBackupService:
    """Handles creating backups periodically. It has a
    staggered versioning scheme and the option to keep all changes in between
    backups.

    The service connects to the per-TLA changes channel (i.e. receives
    change-sets on every user action. These changes are stored in the
    thread-safe _change_buffer and periodically saved to disk at a
    page-specific tmp_changes_path.
     This action (done in self.process_changes), backup_changed_pages and
     prune_all are scheduled and executed in a worker thread.

     Backing up saves the changed pages in the respective backup folders and
     moves the change objects (stored in tmp_changes_file) to a 'changes' file
     which has the to/from timestamps in it's name.

     Pruning removes backup files according to a staggered versioning scheme.
    I.e. we keep 1 backup for every hour of the first day, 1 per day for the
    first week and one per week after that. When pruning backups - the
    'changes' files inbetween get merged.

    Backups older than the PERMANENT_BACKUP_AGE (1 year) get moved to a yearly
    folder (along with the 'changes' files).

    The backup service has a locking mechanism with a file to avoid running
    multiple services. But that may change in the future.

    Timestamps of the last pruning and last backup operations are kept as files
    in order to schedule the next respective operation correctly.

    The backups are stored in per-page folders. Inside them old/permanent
    backups and changes are stored in per year folders.
     """

    def __init__(self,
                 backup_folder: Path,
                 change_set_channel: Channel = None,
                 record_all_changes: bool = False,
                 process_interval: float = PROCESS_INTERVAL,
                 backup_interval: float = BACKUP_INTERVAL,
                 prune_interval: float = PRUNE_INTERVAL,
                 permanent_backup_age: float = PERMANENT_BACKUP_AGE) -> None:
        self.id = get_new_id()

        self.backup_folder: Path = Path(backup_folder)
        self.backup_folder.mkdir(exist_ok=True, parents=True)
        self.change_set_channel = change_set_channel
        self.record_all_changes = record_all_changes

        self.process_interval = process_interval
        self.backup_interval = backup_interval
        self.prune_interval = prune_interval
        self.permanent_backup_age = permanent_backup_age

        self._changed_page_ids: set = set()
        self.stop_event = threading.Event()

        if not shutil.which('git'):
            raise Exception(
                'The backup service depends on git. Install it please.')
        self.change_sub = None

        self.worker_thread = threading.Thread()
        self.scheduler = sched.scheduler(time.time, time.sleep)

        self._change_buffer: list[Change] = []
        self.buffer_lock = threading.Lock()

    def prune_timestamp_path(self) -> Path:
        return self.backup_folder / 'last_prune_timestamp.txt'

    def backup_timestamp_path(self) -> Path:
        return self.backup_folder / 'last_backup_timestamp.txt'

    def service_lock_path(self) -> Path:
        return self.backup_folder / 'backup_service_lock'

    def page_backup_folder(self, page_id: str) -> Path:
        return self.backup_folder / page_id

    def tmp_changes_path(self, page_id) -> Path:
        return self.page_backup_folder(page_id) / 'tmp_changes.jsonl'

    def recents_path(self, page_id: str) -> Path:
        return self.page_backup_folder(page_id) / 'recent_changes.jsonl'

    def recent_backup_path(self, page_id, time: datetime) -> Path:
        name = f'{BACKUP}_{timestamp(time)}.json'
        return self.page_backup_folder(page_id) / name

    def permanent_backups_folder(self, page_id, time: datetime) -> Path:
        return self.page_backup_folder(page_id) / str(time.year)

    def permanent_backup_path(self, page_id, time: datetime) -> Path:
        name = f'{BACKUP}_{timestamp(time)}.json'
        return self.permanent_backups_folder(page_id, time) / name

    def changes_path(self, page_id, from_time: datetime,
                     to_time: datetime) -> Path:
        from_timestamp = timestamp(from_time)
        to_timestamp = timestamp(to_time)
        file_name = f'{CHANGES}_{from_timestamp}_{to_timestamp}.jsonl'
        path = self.page_backup_folder(page_id) / file_name
        return path

    def page_backup_folders(self):
        for page_folder in self.backup_folder.iterdir():
            if not page_folder.is_dir():
                continue
            yield page_folder

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

    def changes_files_for_page(self, page_id) -> List[Path]:
        page_backup_folder = self.page_backup_folder(page_id)
        if not page_backup_folder.exists():
            return []

        change_files = []
        for file in page_backup_folder.iterdir():
            if not file.name.startswith(CHANGES):
                continue
            change_files.append(file)

        return sorted(change_files,
                      key=lambda b: datetimes_from_changes_path(b)[0])

    def last_backup_time(self, page_id: str) -> datetime:
        """Returns the timestamp of the most recent backup for a page as a
        datetime object."""

        last_timestamp = None
        for file in self.recent_backups_for_page(page_id):
            backup_dt = datetime_from_backup_path(file)
            if not last_timestamp:
                last_timestamp = backup_dt
            elif last_timestamp < backup_dt:
                last_timestamp = backup_dt

        return last_timestamp

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
                log.error(f'Change f{change} has not page id')
                continue

            changes_by_page[page_id].append(change)

        # Save the ids of the changed pages, so that we know what to back up
        self._changed_page_ids.update(changes_by_page.keys())

        for page_id, changes in changes_by_page.items():
            json_strings = []
            for change in changes:
                json_str = json.dumps(change.as_safe_delta_dict())
                json_strings.append(json_str + '\n')
            json_str_all = ''.join(json_strings)
            # for change in changes:
            #     json_strings.append(json.dumps(change.as_safe_delta_dict()))
            # json_str_all = '\n'.join(json_strings)

            tmp_changes_path = self.tmp_changes_path(page_id)
            tmp_changes_path.parent.mkdir(parents=True, exist_ok=True)
            with open(tmp_changes_path, 'a') as tmp_changes_file:
                tmp_changes_file.write(json_str_all)

    def backup_changed_pages(self):
        """Saves the pages marked as changes (in self._changed_page_ids) as
        backup copies and if configured to do so - also saves the change
        objects in files between backups in order to have a fill history."""
        # Move the recent changes to backup files
        for page_id in self._changed_page_ids:
            # Serialize the page
            page = pamet.page(id=page_id)
            notes = page.notes()
            arrows = page.arrows()
            page_str = FSStorageRepository.serialize_page(page, notes, arrows)
            last_backup_time = self.last_backup_time(page_id)

            # Create the backup file
            now = current_time()
            backup_file_path = self.recent_backup_path(page_id, now)
            backup_file_path.parent.mkdir(parents=True, exist_ok=True)
            if backup_file_path.exists():
                error_msg = f'A file already exists at {backup_file_path}'
                log.error(error_msg)
                raise Exception(error_msg)
            backup_file_path.write_text(page_str)

            # If configured to do so - create the changes file
            if not self.record_all_changes:
                continue

            if not last_backup_time:  # If there's no previous backups - drop
                self.tmp_changes_path(page_id).unlink()
                continue

            changes_file_path = self.changes_path(page_id, last_backup_time,
                                                  now)
            self.tmp_changes_path(page_id).rename(changes_file_path)
        self._changed_page_ids.clear()

        self.backup_timestamp_path().write_text(timestamp(current_time()))

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
        change_paths_by_to_times = {}
        for file_path in self.page_backup_folder(page_id).iterdir():
            if file_path.name.startswith(CHANGES):
                from_time, to_time = datetimes_from_changes_path(file_path)
                change_paths_by_to_times[to_time] = file_path

        # We're assuming they're already cleaned a week apart
        # If not - big deal
        for backup in for_permanent_backup:
            folder = self.permanent_backups_folder(page_id, backup.datetime)
            folder.mkdir(parents=True, exist_ok=True)
            new_path = folder / backup.path.name
            backup.path.rename(new_path)
            log.info(f'Moved backup {backup.path.name} '
                     'to the yearly folder {folder}')

            # Also move the corresponding changes file if any
            changes_path = change_paths_by_to_times.get(backup.datetime)
            if changes_path:
                changes_path.rename(folder / changes_path.name)

    def prune_all(self):
        """Calls the pruning method for all pages."""
        for page_folder in self.page_backup_folders():
            self.prune_page_backups(page_folder.name)
            self.move_to_permanent_where_appropriate(page_folder.name)

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
        last_year = []
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
                last_year.append(backup)

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
            week = backup.datetime.isocalendar()[1]
            by_week[week].append(backup)

        for_removal = []
        for_keeping = []
        for by_interval in [by_hour, by_day, by_week]:  # Just so its DRY
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
            log.info(f'Removed backup {backup.path}')

        # Merge the changes for the intervals where backups were deleted
        if self.record_all_changes:
            backup_paths = [b.path for b in for_keeping]
            self.merge_changes_with_loose_ends(page_id,
                                               backup_paths=backup_paths)

        # Update the timestamp
        self.prune_timestamp_path().write_text(now.isoformat())

    # def _merge_changes_chain(self, page_id: str, merge_chain: List[Tuple]):

    def merge_changes_with_loose_ends(self, page_id, backup_paths: List[Path]):
        # Parse all the change files, and merge those who don't have a backup
        # file on both sides.
        # A sanity check is performed: wether their timestamps chain properly

        # Populate the changes files fils
        changes_times_by_path = {}
        page_folder = self.page_backup_folder(page_id)
        for file_path in page_folder.iterdir():
            if file_path.name.startswith(CHANGES) and file_path.is_file():
                changes_times_by_path[file_path] = \
                    datetimes_from_changes_path(file_path)

        # Sort the changes, remove those who don't need merging
        # and do an integrity check

        # Sort the changes by from_time
        sorted_change_times_and_paths = sorted(changes_times_by_path.items(),
                                               key=lambda meta: meta[1][0])

        kept_backups_times = [
            datetime_from_backup_path(b) for b in backup_paths
        ]
        merge_chain = []
        for change_path, (from_time, to_time) in sorted_change_times_and_paths:
            # If there's a backup on both sides of a changes chunk -
            # no merging is needed. If there's already a chain started -
            # we execute the merge
            left_is_loose = not (from_time in kept_backups_times)
            right_is_loose = not (to_time in kept_backups_times)
            if not left_is_loose and not right_is_loose:
                if merge_chain:
                    raise Exception
                continue

            elif not left_is_loose and right_is_loose:
                if merge_chain:
                    raise Exception
                merge_chain.append((change_path, from_time, to_time))
                continue

            elif left_is_loose and right_is_loose:
                merge_chain.append((change_path, from_time, to_time))

            else:  # left_is loose and not right_is_loose
                merge_chain.append((change_path, from_time, to_time))
                # self._merge_changes_chain(page_id, merge_chain)
                descr = """Merges the contents of the 'changes' files in the chain and writes
                those in a new 'changes' file with the proper timestamps. Then deletes
                the source files from the chain"""

                # If the "chain" is of only one element - something's fishy
                # When we remove a backup there shoud be at least two loose
                # changes files
                if len(merge_chain) == 1:
                    raise Exception('Inconsistency in changes files. '
                                    f'Merge chain: {merge_chain}')

                # Get the merged changes file name (from the first from_time and
                # last to_time in the chain)
                first_changes_file_meta = merge_chain[0]
                last_changes_file_meta = merge_chain[-1]
                _, outer_left_datetime, _ = first_changes_file_meta
                _, _, outer_right_datetime = last_changes_file_meta
                merged_changes_path = self.changes_path(
                    page_id, outer_left_datetime, outer_right_datetime)

                # Get the combined contents of the changes files
                paths = [metadata[0] for metadata in merge_chain]
                content = '\n'.join(
                    [path.read_text().rstrip() for path in paths])

                # Write the merged changes to the new file and delete the old ones
                merged_changes_path.write_text(content)
                for path in paths:
                    path.unlink()
                    merge_chain = []

        if merge_chain:
            # There should be no changes file that does not have a backup
            # corresponding to its to_timestamp at the end of the chain
            raise Exception(
                f'Change files with no corresponding backup: '
                f'{[m[0] for m in merge_chain]}.'
                f'Delete them if you\'re ok with losing that data.')

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
        while timeout > 0:
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
            raise Exception('Another backup service is running. If you\'re'
                            'sure it\'s not - you can delete the lock file: '
                            f'{self.service_lock_path()}')
        self.service_lock_path().write_text(self.id)

        log.info('Starting')

        # Setup the receival of changes from the change channel if one is given
        if self.change_set_channel:
            self.change_sub = self.change_set_channel.subscribe(
                self.handle_change_set)

        # Search for tmp_changes files to populate the _changed_page_ids.
        # I.e. figure out which pages expect a backup because some changes
        # were made before the scheduled backup
        for page_backup_folder in self.page_backup_folders():
            page_id = page_backup_folder.name
            if self.tmp_changes_path(page_id).exists():
                self._changed_page_ids.append(page_id)

        # Get the timestamp for the last backup and schedule accordingly
        backup_ts = self.backup_timestamp_path()
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
        prune_ts = self.prune_timestamp_path()
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

        self.worker_thread = threading.Thread(target=self.scheduler.run)
        self.worker_thread.start()

    def stop(self):
        """Stops the worker thread and unsubscribes from changes."""
        if self.change_sub:
            self.change_sub.unsubscribe()

        for event in self.scheduler.queue:
            self.scheduler.cancel(event=event)
        log.info('Cancelled events.')

        self.stop_event.set()
        self.worker_thread.join()
        self.service_lock_path().unlink()
        log.info('Stopped service.')
