from typing import Callable
from PySide6.QtCore import QTimer
from misli.pubsub.main_loop import MainLoop
from numpy import isin


class QtMainLoop(MainLoop):
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
