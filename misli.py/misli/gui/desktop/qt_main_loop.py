from PySide2.QtCore import QTimer
from misli.core.main_loop import MainLoop


class QtMainLoop(MainLoop):
    def call_delayed(self, callback, delay, args, kwargs):
        QTimer.singleShot(delay * 1000, lambda: callback(*args, **kwargs))
