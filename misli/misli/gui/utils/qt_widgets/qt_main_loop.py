from typing import Callable
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from misli.pubsub.main_loop import MainLoop


class QtMainLoop(MainLoop):
    def __init__(self, app: QApplication):
        self.app = app

    def call_delayed(
            self,
            callback: Callable,
            delay: float = 0,
            args: list = None,
            kwargs: dict = None):

        args = args or []
        kwargs = kwargs or {}

        if not isinstance(callback, Callable):
            raise Exception

        QTimer.singleShot(delay * 1000, lambda: callback(*args, **kwargs))

    def process_events(self):
        self.app.processEvents()

    def loop(self):
        self.app.exec()
