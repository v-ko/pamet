from typing import Callable
from PySide2.QtCore import QTimer
from misli.core.main_loop import MainLoop


class QtMainLoop(MainLoop):
    def call_delayed(
            self, callback: Callable, delay: float, args: list, kwargs: dict):
        QTimer.singleShot(delay * 1000, lambda: callback(*args, **kwargs))
