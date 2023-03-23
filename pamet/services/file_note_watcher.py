from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import sched
import threading
import time
from PySide6.QtCore import QFileSystemWatcher

from watchdog.observers import Observer
from watchdog.events import FileSystemEvent, FileSystemEventHandler

from fusion import fsm
from fusion.libs.entity.change import Change
from fusion.libs.state import ViewState

from pamet.actions import note as note_actions
from pamet.desktop_app.util import resolve_media_url
from pamet.views.note.file.state import FileNoteViewState

SAFE_DELETE_TOLLERANCE = 0.01  # 10 ms


class DummyHandler(FileSystemEventHandler):

    def __init__(self,
                 on_created: callable = None,
                 on_deleted: callable = None,
                 on_modified: callable = None,
                 on_moved: callable = None):
        super().__init__()
        self.on_created = on_created
        self.on_deleted = on_deleted
        self.on_modified = on_modified
        self.on_moved = on_moved

    # def on_any_event(self, event: FileSystemEvent):
    #     print('INOTIFY:', event.event_type, event.src_path, event.is_directory)


class FileWatcherMode(Enum):
    WATCHING_FILE = 1
    WATCHING_DIR = 2
    DISABLED = 3


@dataclass
class FileWatcher:
    """ Helper class for calling the file preview reload.

    When the file is deleted, we start watching the
    directory for it's reappearance (since a lot of processes do modifications
    by tmp files, deletion of the original and renaming of the tmp file)."""

    def __init__(self, watcher_service, state) -> None:
        self.watcher_service = watcher_service
        self.state = state

        self.current_handler = None
        self._deleted = False
        self.mode = FileWatcherMode.DISABLED

        path = resolve_media_url(self.state.local_image_url)
        if not path.exists() or not path.parent.exists():
            raise Exception(f'File does not exist: {path}')
        self._path = path

        self.set_mode(FileWatcherMode.WATCHING_FILE)

    def __repr__(self):
        return f'<FileWatcher path={self._path} view_id={self.state.view_id}>'

    def request_preview_reload(self, event):
        # print(f'Requesting preview reload. Event: {event}')
        view_state = fsm.view_state(self.state.view_id)
        note_actions.request_file_preview_reload(view_state)

    def set_mode(self, mode: FileWatcherMode):
        # print(f'Setting {self} to mode {mode}')
        if self.current_handler:
            self.watcher_service.remove_handler(self.current_handler)
            self.current_handler = None

        if mode == FileWatcherMode.WATCHING_FILE:
            self.current_handler = DummyHandler(
                on_created=self.request_preview_reload,
                on_deleted=self.handle_immediate_delete,
                on_modified=self.request_preview_reload,
                on_moved=self.request_preview_reload)
            self.watcher_service.watch(
                self._path, self.current_handler)

        elif mode == FileWatcherMode.WATCHING_DIR:
            self.current_handler = DummyHandler(
                on_created=self.check_if_file_reemerged)
            self.watcher_service.watch(
                self._path.parent, self.current_handler)

    def handle_immediate_delete(self, event):
        # print(f'Delete event: {event}')
        self._deleted = True
        self.set_mode(FileWatcherMode.WATCHING_DIR)
        self.watcher_service.request_file_exists_check(self)

    def check_if_file_reemerged(self, event=None):
        # print(f'File {self._path} reemerged: {bool(self._path.exists())}')
        if self._path.exists():
            self._deleted = False
            self.set_mode(FileWatcherMode.WATCHING_FILE)

    def maybe_confirm_deletion(self):
        # print(f'Maybe confirming deletion: {self._path}')
        if self._deleted:
            # print('DELETED!')
            self.on_deleted()


class FileNoteWatcherService:

    def __init__(self):
        self._observer = Observer()
        self.fs_watcher = QFileSystemWatcher()

        # # File recheck scheduler
        self.scheduler = sched.scheduler(time.time, time.sleep)
        self.scheduler_thread = None
        self.quit_scheduler_loop = threading.Event()

        self.file_watchers_by_view_id = {}

        self.watches_by_path = {}
        self.handlers_by_watch = defaultdict(list)
        self.watches_by_handler = {}

        # Connect to state and url changes
        fsm.state_changes_per_TLA_by_view_id.subscribe(
            self.handle_state_change)

    def handle_state_change(self, change: Change):
        """Add/remove/update watches for the respective view state changes. """
        state = change.last_state()
        if not isinstance(state, FileNoteViewState):  # Should be a mixin
            return

        if change.is_create():
            self.watch_state(state)

        elif change.is_delete():
            self.remove_state_watch(state)

        elif change.updated.local_image_url:
            self.remove_state_watch(state)
            self.watch_state(state)

    def scheduler_loop(self):
        while not self.quit_scheduler_loop.is_set():
            delay = self.scheduler.run(blocking=False)
            if delay is None or delay > 0.5:
                delay = 0.5
            time.sleep(delay)

    def start(self):
        self._observer.start()

        self.scheduler_thread = threading.Thread(target=self.scheduler_loop)
        self.scheduler_thread.start()

    def request_file_exists_check(self, file_watcher: FileWatcher):
        # print(f'Requesting file exists check for {file_watcher}')
        self.scheduler.enter(SAFE_DELETE_TOLLERANCE, 1,
                             file_watcher.check_if_file_reemerged)

    def stop(self):
        self._observer.stop()
        self._observer.join()

        self.quit_scheduler_loop.set()
        self.scheduler_thread.join()

    def watch(self, path: str | Path, handler: FileSystemEventHandler):
        path = Path(path)
        if not path.exists() or not path.parent.exists():
            raise Exception

        path = str(path)
        watch = self.watches_by_path.get(path)
        if watch:
            # print('Path already watched. Adding handler.')
            self._observer.add_handler_for_watch(handler, watch)
        else:
            # print('Path not watched. Adding watch.')
            watch = self._observer.schedule(handler, path, recursive=False)
            self.watches_by_path[path] = watch

        self.handlers_by_watch[watch].append(handler)
        self.watches_by_handler[handler] = watch
        # print(f'Added watch for {path}. Watch: {watch}')

    def remove_handler(self, handler):
        # print(f'Removing handler {handler}')

        # Remove the handler
        watch = self.watches_by_handler.get(handler)
        if not watch:
            raise Exception
        self._observer.remove_handler_for_watch(handler, watch)
        self.handlers_by_watch[watch].remove(handler)
        del self.watches_by_handler[handler]

        # Remove the watch if no handlers are left
        if not self.handlers_by_watch[watch]:
            # print(f'No handlers left for watch. Removing {watch}.')
            self._observer.unschedule(watch)
            del self.handlers_by_watch[watch]
            del self.watches_by_path[watch.path]

    def watch_state(self, state: ViewState):
        # print('Adding watch for state with view_id', state.view_id)
        file_watcher = FileWatcher(self, state)
        self.file_watchers_by_view_id[state.view_id] = file_watcher
        return file_watcher

    def remove_state_watch(self, state: ViewState):
        # print('Removing watch for state with view_id', state.view_id)
        if state.view_id not in self.file_watchers_by_view_id:
            return

        file_watcher = self.file_watchers_by_view_id[state.view_id]
        file_watcher.set_mode(FileWatcherMode.DISABLED)
        del self.file_watchers_by_view_id[state.view_id]
