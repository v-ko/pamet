from typing import Callable


class Context:
    def __init__(self):
        self._entries = {}

    def add(self, name, value):
        self._entries[name] = value

    def add_callable(self, name, function: Callable):
        self._entries[name] = function

    def __getitem__(self, item):
        val = self._entries[item]

        if callable(val):
            val = val()

        return val

    def __iter__(self):
        return iter(self._entries)

    def __len__(self):
        return len(self._entries)
