from datetime import datetime, timedelta

import json
from pathlib import Path
import time
from typing import List

from misli.entity_library.change import Change
from misli.storage.in_memory_repository import InMemoryRepository
import pamet
from misli.helpers import fake_time, current_time
from pamet.model.page import Page
from pamet.model.text_note import TextNote
from pamet.services.backup import FSStorageBackupService
from pamet.storage.file_system.repository import FSStorageRepository

# Debug
PROCESS_INTERVAL = 5
PRUNE_INTERVAL = 15
BACKUP_INTERVAL = 10
PERMANENT_BACKUP_AGE = 30


def test_change_processing(tmp_path):
    backup_service = FSStorageBackupService(backup_folder=tmp_path)

    page = Page(name='test')
    change = Change.CREATE(page)
    backup_service.handle_change_set([change])
    backup_service.process_changes()

    # Assert result
    jsonl_data = backup_service.tmp_changes_path(page.id).read_text()
    json_lines = jsonl_data.split('\n')
    assert json_lines[0] == json.dumps(change.as_safe_delta_dict())


def change_and_backup(backup_service,
                      page,
                      time,
                      note_text: str = 'Test note'):
    note = TextNote()
    note.text = note_text

    change = page.insert_note(note)

    backup_service.handle_change_set([change])
    backup_service.process_changes()
    with fake_time(time=time):
        backup_service.backup_changed_pages()

    return change


def changes_file_is_valid(path, changes):
    change_jsons = [
        json.dumps(change.as_safe_delta_dict()) for change in changes
    ]
    changes_content = path.read_text().rstrip()
    expected_content = '\n'.join(change_jsons)
    return changes_content == expected_content


def test_backup(tmp_path):
    backup_service = FSStorageBackupService(backup_folder=tmp_path,
                                            record_all_changes=True)
    in_mem_repo = InMemoryRepository()
    pamet.set_sync_repo(in_mem_repo)

    page = Page(name='test')
    change = pamet.insert_page(page)
    page_json1 = FSStorageRepository.serialize_page(page, [], [])

    backup_service.handle_change_set([change])
    backup_service.process_changes()
    backup_service.backup_changed_pages()

    backups = list(backup_service.recent_backups_for_page(page.id))
    assert len(backups) == 1
    assert page_json1 == backups[0].read_text()

    note = TextNote()
    note.text = 'Test note'

    change = page.insert_note(note)
    page_json2 = FSStorageRepository.serialize_page(page, [note], [])

    backup_service.handle_change_set([change])
    backup_service.process_changes()
    with fake_time(time=current_time() + timedelta(seconds=1)):
        backup_service.backup_changed_pages()

    backups = list(backup_service.recent_backups_for_page(page.id))
    assert len(backups) == 2
    assert page_json2 == backups[1].read_text()

    changes_files = list(backup_service.changes_files_for_page(page.id))
    assert len(changes_files) == 1
    # lines = changes_files[0].read_text().split('\n')
    # assert lines[0] == json.dumps(change.as_safe_delta_dict())
    assert changes_file_is_valid(changes_files[0], [change])


def test_pruning(tmp_path):
    backup_service = FSStorageBackupService(backup_folder=tmp_path,
                                            record_all_changes=True)

    in_mem_repo = InMemoryRepository()
    pamet.set_sync_repo(in_mem_repo)

    for_removal: List[Path] = []
    for_keeping: List[Path] = []
    change_obj_files = {}  # Change lists, by path

    # Craete the initial backup
    page = Page(name='test')
    change = pamet.insert_page(page)

    initial_backup_time = datetime(year=2099,
                                   month=7,
                                   day=30,
                                   hour=23,
                                   minute=1,
                                   second=0)
    with fake_time(initial_backup_time):
        backup_service.handle_change_set([change])
        backup_service.process_changes()
        backup_service.backup_changed_pages()

    for_keeping.append(
        backup_service.recent_backup_path(page.id, initial_backup_time))

    # Do x2 backups per period (last day, month, year). The older for each
    # Current time when pruning will be 2100.6.30 23:01:00

    # Last year, same week
    # This one should be deleted
    weekly_deleted_time = datetime.fromisocalendar(year=2100, week=10, day=1)
    for_removal.append(
        backup_service.recent_backup_path(page.id, weekly_deleted_time))
    change = change_and_backup(backup_service, page, weekly_deleted_time,
                               'Last year, same week, to be deleted')
    changes = [change]

    # This one should be kept, and the changes up to this point
    # should be merged
    weekly_kept_time = datetime.fromisocalendar(year=2100, week=10, day=2)
    change = change_and_backup(backup_service, page, weekly_kept_time,
                               'Last year, same week, to be kept')
    for_keeping.append(
        backup_service.recent_backup_path(page.id, weekly_kept_time))
    changes.append(change)
    change_obj_file_path = backup_service.changes_path(page.id,
                                                       initial_backup_time,
                                                       weekly_kept_time)
    change_obj_files[change_obj_file_path] = changes

    # Last month, same day
    # This one should be deleted
    daily_deleted_time = datetime(year=2100,
                                  month=6,
                                  day=15,
                                  hour=2,
                                  minute=1,
                                  second=0)
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
                               second=0)
    for_keeping.append(
        backup_service.recent_backup_path(page.id, daily_kept_time))
    change = change_and_backup(backup_service, page, daily_kept_time,
                               'Last month, same day, to be kept')
    changes.append(change)
    change_obj_file_path = backup_service.changes_path(page.id,
                                                       weekly_kept_time,
                                                       daily_kept_time)
    change_obj_files[change_obj_file_path] = changes

    # Last day, same hour
    # This one should be deleted
    hourly_deleted_time = datetime(year=2100,
                                   month=6,
                                   day=30,
                                   hour=15,
                                   minute=1,
                                   second=0)
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
                                second=0)
    for_keeping.append(
        backup_service.recent_backup_path(page.id, hourly_kept_time))
    change = change_and_backup(backup_service, page, hourly_kept_time,
                               'Last day, same hour, to be kept')
    changes.append(change)
    change_obj_file_path = backup_service.changes_path(page.id,
                                                       daily_kept_time,
                                                       hourly_kept_time)
    change_obj_files[change_obj_file_path] = changes

    # Do pruning
    with fake_time(
            datetime(year=2100, month=6, day=30, hour=23, minute=1, second=0)):
        backup_service.prune_page_backups(page.id)

    # Assert file counts and changes-file contents
    assert len(for_keeping) == len(
        backup_service.recent_backups_for_page(page.id))

    for backup_path in for_keeping:
        assert backup_path.exists()
    for backup_path in for_removal:
        assert not backup_path.exists()

    assert len(backup_service.changes_files_for_page(
        page.id)) == len(change_obj_files)

    for path, changes in change_obj_files.items():
        assert changes_file_is_valid(path, changes)


def test_permanent_storage(tmp_path):
    backup_service = FSStorageBackupService(backup_folder=tmp_path)

    in_mem_repo = InMemoryRepository()
    pamet.set_sync_repo(in_mem_repo)

    # Craete the initial backup
    page = Page(name='test')
    change = pamet.insert_page(page)

    initial_backup_time = datetime(year=2000, month=7, day=30)
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

    in_mem_repo = InMemoryRepository()
    pamet.set_sync_repo(in_mem_repo)

    backup_service = FSStorageBackupService(backup_folder=tmp_path,
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
    assert backup_service.tmp_changes_path(page.id).exists()

    time.sleep(1)
    assert bool(backup_service.last_backup_time(page.id))

    # time_requesting_stop = time.time()
    backup_service.stop()
    # time_stopped = time.time()
    assert not backup_service.service_lock_path().exists()

    assert backup_service.backup_timestamp_path().exists()
    assert backup_service.prune_timestamp_path().exists()
