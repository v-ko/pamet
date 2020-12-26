from typing import Callable
import time


class MainLoop:
    def call_delayed(
            self, callback: Callable, delay: float, args: list, kwargs: dict):
        raise NotImplementedError


class NoMainLoop(MainLoop):
    def __init__(self):
        self.callback_stack = []

    def call_delayed(
            self, callback: Callable, delay: float, args: list, kwargs: dict):
        self.callback_stack.append(
            (callback, time.time() + delay, args, kwargs))

    def process_events(self):
        for callback, call_time, args, kwargs in self.callback_stack:
            if time.time() >= call_time:
                callback(*args, **kwargs)
