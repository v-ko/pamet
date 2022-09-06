from datetime import datetime, timedelta

import json
from pathlib import Path
import time
from typing import List

from fusion.libs.entity.change import Change

import pamet
from fusion.util import fake_time, current_time
from pamet.model.page import Page
from pamet.model.text_note import TextNote
from pamet.services.backup import FSStorageBackupService
from pamet.storage.file_system.repository import FSStorageRepository
from pamet.storage.pamet_in_memory_repo import PametInMemoryRepository

# Debug
PROCESS_INTERVAL = 5
PRUNE_INTERVAL = 15
BACKUP_INTERVAL = 10
PERMANENT_BACKUP_AGE = 30


def test_change_processing(tmp_path):
    backup_service = FSStorageBackupService(
        backup_folder=tmp_path, repository=PametInMemoryRepository())

    page = Page(name='test')
    change = Change.CREATE(page)
    backup_service.handle_change_set([change])
    backup_service.process_changes()

    # Assert result
    jsonl_data = backup_service.tmp_changeset_path(page.id).read_text()
    json_lines = jsonl_data.split('\n')
    assert json_lines[0] == json.dumps(change.as_safe_delta_dict(),
                                       ensure_ascii=False)


def change_and_backup(backup_service,
                      page,
                      time,
                      note_text: str = 'Test note'):
    note = TextNote.in_page(page)
    note.text = note_text
    with fake_time(time=time):
        change = pamet.insert_note(note, page)

        backup_service.handle_change_set([change])
        backup_service.process_changes()
        backup_service.backup_changed_pages()

    return change


def changes_are_identical(changeset1, changeset2):
    changeset1 = sorted(changeset1, key=lambda change: change.id)
    changeset1 = [change.as_safe_delta_dict() for change in changeset1]

    changeset2 = sorted(changeset2, key=lambda change: change.id)
    changeset2 = [change.as_safe_delta_dict() for change in changeset2]
    return changeset1 == changeset2


def test_backup(tmp_path):
    in_mem_repo = PametInMemoryRepository()
    backup_service = FSStorageBackupService(backup_folder=tmp_path,
                                            repository=in_mem_repo,
                                            record_all_changes=True)
    pamet.set_sync_repo(in_mem_repo)

    page = Page(name='test')
    change1 = pamet.insert_page(page)
    page_json1 = FSStorageRepository.serialize_page(page, [], [])

    backup_service.handle_change_set([change1])
    backup_service.process_changes()
    backup_service.backup_changed_pages()

    backups = list(backup_service.recent_backups_for_page(page.id))
    assert len(backups) == 1
    assert page_json1 == backups[0].read_text()

    note = TextNote.in_page(page)
    note.text = 'Test note'

    change2 = pamet.insert_note(note, page)
    page_json2 = FSStorageRepository.serialize_page(page, [note], [])

    backup_service.handle_change_set([change2])
    backup_service.process_changes()
    with fake_time(time=current_time() + timedelta(seconds=1)):
        backup_service.backup_changed_pages()

    backups = list(backup_service.recent_backups_for_page(page.id))
    assert len(backups) == 2
    assert page_json2 == backups[1].read_text()

    # changes_files = list(backup_service.changeset_paths_for_page(page.id))
    # assert len(changes_files) == 1
    # lines = changes_files[0].read_text().split('\n')
    # assert lines[0] == json.dumps(change.as_safe_delta_dict())
    changes = backup_service.get_changes()
    assert changes_are_identical(changes, [change1, change2])


def test_pruning(tmp_path):
    in_mem_repo = PametInMemoryRepository()
    backup_service = FSStorageBackupService(backup_folder=tmp_path,
                                            repository=in_mem_repo,
                                            record_all_changes=True)

    pamet.set_sync_repo(in_mem_repo)

    for_removal: List[Path] = []
    for_keeping: List[Path] = []
    change_obj_files = {}  # Change lists, by path

    # Craete the initial backup
    page = Page(name='test')
    page2 = Page(name='test2')  # To test page_id filtering for .get_changes()

    initial_backup_time = datetime(year=2099,
                                   month=7,
                                   day=30,
                                   hour=23,
                                   minute=1,
                                   second=0).astimezone()
    with fake_time(initial_backup_time):
        page1_change = pamet.insert_page(page)
        page2_change = pamet.insert_page(page2)
        backup_service.handle_change_set([page1_change, page2_change])
        backup_service.process_changes()
        backup_service.backup_changed_pages()

    for_keeping.append(
        backup_service.recent_backup_path(page.id, initial_backup_time))

    # Do x2 backups per period (last day, month, year). The older for each
    # Current time when pruning will be 2100.6.30 23:01:00

    # Last year, same week
    # This one should be deleted
    weekly_deleted_time = datetime.fromisocalendar(year=2100, week=10,
                                                   day=1).astimezone()
    for_removal.append(
        backup_service.recent_backup_path(page.id, weekly_deleted_time))
    change = change_and_backup(backup_service, page, weekly_deleted_time,
                               'Last year, same week, to be deleted')
    changes = [change]

    # This one should be kept, and the changes up to this point
    # should be merged
    weekly_kept_time = datetime.fromisocalendar(year=2100, week=10,
                                                day=2).astimezone()
    change = change_and_backup(backup_service, page, weekly_kept_time,
                               'Last year, same week, to be kept')
    for_keeping.append(
        backup_service.recent_backup_path(page.id, weekly_kept_time))
    changes.append(change)
    change_obj_files[weekly_kept_time] = changes

    # Last month, same day
    # This one should be deleted
    daily_deleted_time = datetime(year=2100,
                                  month=6,
                                  day=15,
                                  hour=2,
                                  minute=1,
                                  second=0).astimezone()
    change = change_and_backup(backup_service, page, daily_deleted_time,
                               'Last month, same day, to be deleted')
    for_removal.append(
        backup_service.recent_backup_path(page.id, daily_deleted_time))
    changes = [change]

    # This one should be kept, and the changes up to this point
    # should be merged
    daily_kept_time = datetime(year=2100,
                               month=6,
                               day=15,
                               hour=14,
                               minute=1,
                               second=0).astimezone()
    for_keeping.append(
        backup_service.recent_backup_path(page.id, daily_kept_time))
    change = change_and_backup(backup_service, page, daily_kept_time,
                               'Last month, same day, to be kept')
    changes.append(change)
    change_obj_files[daily_kept_time] = changes

    # Last day, same hour
    # This one should be deleted
    hourly_deleted_time = datetime(year=2100,
                                   month=6,
                                   day=30,
                                   hour=15,
                                   minute=1,
                                   second=0).astimezone()
    for_removal.append(
        backup_service.recent_backup_path(page.id, hourly_deleted_time))
    change = change_and_backup(backup_service, page, hourly_deleted_time,
                               'Last day, same hour, to be deleted')
    changes = [change]

    # This one should be kept
    hourly_kept_time = datetime(year=2100,
                                month=6,
                                day=30,
                                hour=15,
                                minute=20,
                                second=0).astimezone()
    for_keeping.append(
        backup_service.recent_backup_path(page.id, hourly_kept_time))
    change = change_and_backup(backup_service, page, hourly_kept_time,
                               'Last day, same hour, to be kept')
    changes.append(change)
    change_obj_files[hourly_kept_time] = changes

    # Do pruning
    with fake_time(
            datetime(year=2100, month=6, day=30, hour=23, minute=1,
                     second=0).astimezone()):
        backup_service.prune_page_backups(page.id)

    # Assert file counts and changes-file contents
    assert len(for_keeping) == len(
        backup_service.recent_backups_for_page(page.id))

    for backup_path in for_keeping:
        assert backup_path.exists()
    for backup_path in for_removal:
        assert not backup_path.exists()

    # Check if all changes are present and valid
    all_changes = []
    for change_path, changes in change_obj_files.items():
        all_changes.extend(changes)
    all_changes.extend([page1_change, page2_change])

    saved_changes = backup_service.get_changes()
    assert changes_are_identical(saved_changes, all_changes)

    # Check if the get_change filtering is working
    # Check for page_id filtering
    page2_changes = backup_service.get_changes(page_id=page2.id)
    assert changes_are_identical(page2_changes, [page2_change])

    # Chech for filtering by time
    all_changes = sorted(all_changes, key=lambda c: c.time)
    after_time = weekly_deleted_time
    before_time = hourly_deleted_time

    subset = list(
        filter(lambda c: after_time <= c.time < before_time, all_changes))
    retrieved = backup_service.get_changes(after_time=after_time,
                                           before_time=before_time)
    assert changes_are_identical(subset, retrieved)


def test_permanent_storage(tmp_path):
    in_mem_repo = PametInMemoryRepository()
    backup_service = FSStorageBackupService(backup_folder=tmp_path,
                                            repository=in_mem_repo)

    pamet.set_sync_repo(in_mem_repo)

    # Craete the initial backup
    page = Page(name='test')
    change = pamet.insert_page(page)

    initial_backup_time = datetime(year=2000, month=7, day=30).astimezone()
    with fake_time(initial_backup_time):
        backup_service.handle_change_set([change])
        backup_service.process_changes()
        backup_service.backup_changed_pages()

    backup_service.move_to_permanent_where_appropriate(page.id)

    assert not backup_service.recent_backups_for_page(page.id)
    assert backup_service.permanent_backup_path(page.id,
                                                initial_backup_time).exists()


def test_sheduler_and_worker(tmp_path):
    # Test the scheduler, worker thread and changes channel.
    # Just do a single backup and check it along with the backup/prune
    # timesetamps

    in_mem_repo = PametInMemoryRepository()
    pamet.set_sync_repo(in_mem_repo)

    backup_service = FSStorageBackupService(backup_folder=tmp_path,
                                            repository=in_mem_repo,
                                            process_interval=0.5,
                                            backup_interval=1,
                                            prune_interval=1.5)
    # Start the service
    backup_service.start()
    # time_started = time.time()
    assert backup_service.service_lock_path().exists()

    # Enter a change
    page = Page(name='test')
    change = pamet.insert_page(page)
    backup_service.handle_change_set([change])

    # Wait for the process_events
    time.sleep(0.6)
    assert backup_service.tmp_changeset_path(page.id).exists()

    time.sleep(1)
    assert bool(backup_service.last_backup_time(page.id))

    # time_requesting_stop = time.time()
    backup_service.stop()
    # time_stopped = time.time()
    assert not backup_service.service_lock_path().exists()

    assert backup_service.last_backup_timestamp_path().exists()
    assert backup_service.last_prune_timestamp_path().exists()
