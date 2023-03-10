from pathlib import Path
import time

# from PySide6.QtCore import QFileSystemWatcher
# from PySide6.QtWidgets import QApplication
from watchdog.observers import Observer
from watchdog.events import FileSystemEvent, FileSystemEventHandler


class FSWatchEventHandler(FileSystemEventHandler):
    def on_created(self, event):
        print('Created', event)

    def on_deleted(self, event):
        print('deleted', event)

    def on_modified(self, event):
        print('modified', event)

    def on_moved(self, event):
        print('moved', event)

    def on_any_event(self, event: FileSystemEvent):
        print('ANY:', event.event_type, event.src_path, event.is_directory)


class FSWatcherService:
    def __init__(self, folder: str | Path):
        self.folder = Path(folder).expanduser()
        if not self.folder.exists() or not self.folder.is_dir():
            raise Exception

        self.observer = Observer()
        event_handler = FSWatchEventHandler()
        observer = Observer()
        observer.schedule(event_handler, self.folder, recursive=False)
        observer.start()

    def start(self):
        self.observer.start()

    def stop(self):
        self.observer.stop()
        self.observer.join()

# class FSWatcherService(QFileSystemWatcher):
#     def __init__(self, folder: str | Path):
#         super().__init__()
#         self.folder = Path(folder).expanduser()
#         if not self.folder.exists() or not self.folder.is_dir():
#             raise Exception

#         self.addPath(str(self.folder))
#         self.fileChanged.connect(self.handle_file_changed)
#         self.directoryChanged.connect(self.handle_directory_changed)

#     def handle_file_changed(self, file_path):
#         file_path = Path(file_path)
#         print('file changed', file_path)

#     def handle_directory_changed(self, directory_path):
#         directory_path = Path(directory_path)
#         print('directory changed', directory_path)


# Test
if __name__ == '__main__':
    # app = QApplication()
    fs_watcher = FSWatcherService('~/fs_test')
    # app.exec()
    fs_watcher.start()
    try:
        while True:
            time.sleep(1)
    finally:
        fs_watcher.stop()
